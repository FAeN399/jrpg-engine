"""
Typed event bus for decoupled communication.

Uses Enums for event types to prevent magic strings and enable
IDE autocomplete. This is critical for AI-assisted development.

Usage:
    # Define events
    class GameEvents(Enum):
        PLAYER_DAMAGED = auto()
        ITEM_COLLECTED = auto()

    # Subscribe
    event_bus.subscribe(GameEvents.PLAYER_DAMAGED, on_player_damaged)

    # Publish
    event_bus.publish(GameEvents.PLAYER_DAMAGED, damage=10, source=enemy)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable
from weakref import WeakMethod, ref


# Core engine events
class EngineEvent(Enum):
    """Built-in engine events."""
    # Lifecycle
    GAME_START = auto()
    GAME_PAUSE = auto()
    GAME_RESUME = auto()
    GAME_QUIT = auto()

    # Scene
    SCENE_PUSHED = auto()
    SCENE_POPPED = auto()
    SCENE_SWITCHED = auto()

    # Window
    WINDOW_RESIZED = auto()
    WINDOW_FOCUS_GAINED = auto()
    WINDOW_FOCUS_LOST = auto()

    # Entity
    ENTITY_CREATED = auto()
    ENTITY_DESTROYED = auto()
    COMPONENT_ADDED = auto()
    COMPONENT_REMOVED = auto()


class AudioEvent(Enum):
    """Audio system events."""
    BGM_STARTED = auto()
    BGM_STOPPED = auto()
    BGM_CROSSFADE = auto()
    SFX_PLAYED = auto()


class UIEvent(Enum):
    """UI system events."""
    MENU_OPENED = auto()
    MENU_CLOSED = auto()
    DIALOG_STARTED = auto()
    DIALOG_ENDED = auto()
    WIDGET_FOCUSED = auto()
    WIDGET_UNFOCUSED = auto()
    BUTTON_CLICKED = auto()
    SELECTION_CHANGED = auto()
    TEXT_INPUT = auto()
    INVENTORY_OPENED = auto()
    INVENTORY_CLOSED = auto()
    SHOP_OPENED = auto()
    SHOP_CLOSED = auto()


@dataclass
class Event:
    """
    Event data container.

    Attributes:
        type: The event type (Enum member)
        data: Dictionary of event-specific data
        consumed: Whether the event has been handled
    """
    type: Enum
    data: dict[str, Any] = field(default_factory=dict)
    consumed: bool = False

    def consume(self) -> None:
        """Mark event as consumed (stops propagation)."""
        self.consumed = True

    def get(self, key: str, default: Any = None) -> Any:
        """Get event data by key."""
        return self.data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Get event data by key (dict-style)."""
        return self.data[key]


# Type alias for event handlers
EventHandler = Callable[[Event], None]


class EventBus:
    """
    Central event bus for publish/subscribe messaging.

    Features:
    - Typed events (Enum-based)
    - Priority ordering
    - Weak references (auto-cleanup when handlers are deleted)
    - One-shot handlers
    - Event consumption (stops propagation)
    """

    def __init__(self):
        # Map of event type -> list of (priority, handler, one_shot)
        self._handlers: dict[Enum, list[tuple[int, Any, bool]]] = {}
        # Queue for events published during handling
        self._event_queue: list[Event] = []
        self._is_publishing = False

    def subscribe(
        self,
        event_type: Enum,
        handler: EventHandler,
        priority: int = 0,
        one_shot: bool = False,
        weak: bool = True,
    ) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: The event type to listen for
            handler: Callback function(event: Event)
            priority: Higher priority handlers are called first (default 0)
            one_shot: If True, handler is removed after first call
            weak: If True, use weak reference (handler auto-removed if deleted)
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        # Create weak reference if requested
        if weak:
            if hasattr(handler, '__self__'):
                # Method - use WeakMethod
                handler_ref = WeakMethod(handler)
            else:
                # Function - use regular ref
                handler_ref = ref(handler)
        else:
            handler_ref = handler

        # Insert sorted by priority (highest first)
        handlers = self._handlers[event_type]
        entry = (priority, handler_ref, one_shot)

        # Find insertion point
        insert_idx = 0
        for i, (p, _, _) in enumerate(handlers):
            if priority > p:
                insert_idx = i
                break
            insert_idx = i + 1

        handlers.insert(insert_idx, entry)

    def unsubscribe(self, event_type: Enum, handler: EventHandler) -> None:
        """
        Unsubscribe from an event type.

        Args:
            event_type: The event type
            handler: The handler to remove
        """
        if event_type not in self._handlers:
            return

        handlers = self._handlers[event_type]
        self._handlers[event_type] = [
            (p, h, o) for p, h, o in handlers
            if self._get_handler(h) != handler
        ]

    def publish(self, event_type: Enum, **data: Any) -> Event:
        """
        Publish an event.

        Args:
            event_type: The event type
            **data: Event data as keyword arguments

        Returns:
            The Event object (check .consumed to see if it was handled)
        """
        event = Event(type=event_type, data=data)

        if self._is_publishing:
            # Queue event if we're already publishing
            self._event_queue.append(event)
        else:
            self._dispatch(event)

        return event

    def publish_event(self, event: Event) -> None:
        """
        Publish a pre-created event.

        Args:
            event: The event to publish
        """
        if self._is_publishing:
            self._event_queue.append(event)
        else:
            self._dispatch(event)

    def clear(self, event_type: Enum | None = None) -> None:
        """
        Clear handlers.

        Args:
            event_type: If specified, only clear handlers for this type.
                       If None, clear all handlers.
        """
        if event_type is None:
            self._handlers.clear()
        elif event_type in self._handlers:
            del self._handlers[event_type]

    def _dispatch(self, event: Event) -> None:
        """Dispatch event to handlers."""
        if event.type not in self._handlers:
            return

        self._is_publishing = True
        handlers = self._handlers[event.type]
        to_remove = []

        for i, (priority, handler_ref, one_shot) in enumerate(handlers):
            handler = self._get_handler(handler_ref)

            if handler is None:
                # Weak reference was garbage collected
                to_remove.append(i)
                continue

            try:
                handler(event)
            except Exception as e:
                # Log but don't crash
                print(f"Error in event handler for {event.type}: {e}")

            if one_shot:
                to_remove.append(i)

            if event.consumed:
                break

        # Remove dead/one-shot handlers (in reverse order to preserve indices)
        for i in reversed(to_remove):
            handlers.pop(i)

        self._is_publishing = False

        # Process queued events
        while self._event_queue:
            queued = self._event_queue.pop(0)
            self._dispatch(queued)

    def _get_handler(self, handler_ref: Any) -> EventHandler | None:
        """Resolve handler from reference."""
        if callable(handler_ref) and not isinstance(handler_ref, (ref, WeakMethod)):
            # Strong reference
            return handler_ref

        # Weak reference
        result = handler_ref()
        return result
