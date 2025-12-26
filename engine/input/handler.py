"""
Input handler with action-based abstraction.

Handles keyboard, mouse, and gamepad input, translating
raw input into semantic Actions for game logic.

Usage:
    # In game logic
    if input.is_action_pressed(Action.MOVE_RIGHT):
        player.move_right()

    if input.is_action_just_pressed(Action.ATTACK):
        player.attack()

    # Get movement vector
    move = input.get_movement_vector()
    player.velocity = move * speed
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
from enum import Enum

import pygame

from engine.core.actions import (
    Action,
    DEFAULT_KEY_BINDINGS,
    DEFAULT_GAMEPAD_BINDINGS,
    DEFAULT_GAMEPAD_AXIS_BINDINGS,
    DEFAULT_GAMEPAD_HAT_BINDINGS,
)
from engine.core.events import EventBus


class InputEvent(Enum):
    """Input-specific events."""
    ACTION_PRESSED = "input.action_pressed"
    ACTION_RELEASED = "input.action_released"
    MOUSE_MOVED = "input.mouse_moved"
    MOUSE_BUTTON_DOWN = "input.mouse_button_down"
    MOUSE_BUTTON_UP = "input.mouse_button_up"
    MOUSE_WHEEL = "input.mouse_wheel"
    GAMEPAD_CONNECTED = "input.gamepad_connected"
    GAMEPAD_DISCONNECTED = "input.gamepad_disconnected"


@dataclass
class MouseState:
    """Current mouse state."""
    x: int = 0
    y: int = 0
    dx: int = 0  # Delta since last frame
    dy: int = 0
    buttons: tuple[bool, bool, bool] = (False, False, False)
    wheel: int = 0


@dataclass
class InputState:
    """Complete input state for current frame."""
    # Action states
    actions_pressed: set[Action] = field(default_factory=set)
    actions_just_pressed: set[Action] = field(default_factory=set)
    actions_just_released: set[Action] = field(default_factory=set)

    # Raw key states (for edge cases)
    keys_pressed: set[int] = field(default_factory=set)
    keys_just_pressed: set[int] = field(default_factory=set)
    keys_just_released: set[int] = field(default_factory=set)

    # Mouse
    mouse: MouseState = field(default_factory=MouseState)

    # Gamepad analog values
    axis_values: dict[int, float] = field(default_factory=dict)


class InputHandler:
    """
    Handles all input processing.

    Translates raw pygame events into semantic Actions.
    Supports keyboard, mouse, and gamepad.
    """

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus

        # Current and previous frame states
        self._state = InputState()
        self._prev_actions: set[Action] = set()
        self._prev_keys: set[int] = set()

        # Key bindings (action -> list of keys)
        self._key_bindings = DEFAULT_KEY_BINDINGS.copy()
        self._reverse_key_bindings: dict[int, list[Action]] = {}
        self._rebuild_reverse_bindings()

        # Gamepad
        self._gamepads: dict[int, pygame.joystick.JoystickType] = {}
        self._gamepad_bindings = DEFAULT_GAMEPAD_BINDINGS.copy()
        self._gamepad_axis_bindings = list(DEFAULT_GAMEPAD_AXIS_BINDINGS)
        self._gamepad_hat_bindings = DEFAULT_GAMEPAD_HAT_BINDINGS.copy()

        # Initialize gamepads
        pygame.joystick.init()
        self._refresh_gamepads()

        # Input callbacks (for UI systems that need raw input)
        self._text_input_callback: Callable[[str], None] | None = None

    def _rebuild_reverse_bindings(self) -> None:
        """Build reverse lookup: key -> actions."""
        self._reverse_key_bindings.clear()
        for action, keys in self._key_bindings.items():
            for key in keys:
                if key not in self._reverse_key_bindings:
                    self._reverse_key_bindings[key] = []
                self._reverse_key_bindings[key].append(action)

    def _refresh_gamepads(self) -> None:
        """Refresh connected gamepads."""
        self._gamepads.clear()
        for i in range(pygame.joystick.get_count()):
            joy = pygame.joystick.Joystick(i)
            joy.init()
            self._gamepads[joy.get_instance_id()] = joy

    # Public API

    def is_action_pressed(self, action: Action) -> bool:
        """Check if an action is currently held down."""
        return action in self._state.actions_pressed

    def is_action_just_pressed(self, action: Action) -> bool:
        """Check if an action was just pressed this frame."""
        return action in self._state.actions_just_pressed

    def is_action_just_released(self, action: Action) -> bool:
        """Check if an action was just released this frame."""
        return action in self._state.actions_just_released

    def is_key_pressed(self, key: int) -> bool:
        """Check if a raw key is pressed."""
        return key in self._state.keys_pressed

    def is_key_just_pressed(self, key: int) -> bool:
        """Check if a raw key was just pressed."""
        return key in self._state.keys_just_pressed

    def get_movement_vector(self) -> tuple[float, float]:
        """
        Get normalized movement vector from input.

        Returns:
            (x, y) tuple where each component is -1, 0, or 1
        """
        x = 0.0
        y = 0.0

        if self.is_action_pressed(Action.MOVE_LEFT):
            x -= 1.0
        if self.is_action_pressed(Action.MOVE_RIGHT):
            x += 1.0
        if self.is_action_pressed(Action.MOVE_UP):
            y -= 1.0
        if self.is_action_pressed(Action.MOVE_DOWN):
            y += 1.0

        # Normalize diagonal movement
        if x != 0 and y != 0:
            x *= 0.7071  # 1/sqrt(2)
            y *= 0.7071

        return (x, y)

    def get_menu_direction(self) -> tuple[int, int]:
        """
        Get menu navigation direction (just pressed).

        Returns:
            (dx, dy) where each is -1, 0, or 1
        """
        dx = 0
        dy = 0

        if self.is_action_just_pressed(Action.MENU_LEFT):
            dx = -1
        elif self.is_action_just_pressed(Action.MENU_RIGHT):
            dx = 1

        if self.is_action_just_pressed(Action.MENU_UP):
            dy = -1
        elif self.is_action_just_pressed(Action.MENU_DOWN):
            dy = 1

        return (dx, dy)

    @property
    def mouse(self) -> MouseState:
        """Get current mouse state."""
        return self._state.mouse

    @property
    def mouse_pos(self) -> tuple[int, int]:
        """Get mouse position."""
        return (self._state.mouse.x, self._state.mouse.y)

    def get_axis(self, axis: int) -> float:
        """Get gamepad axis value (-1 to 1)."""
        return self._state.axis_values.get(axis, 0.0)

    # Key binding management

    def bind_key(self, action: Action, key: int) -> None:
        """Add a key binding for an action."""
        if action not in self._key_bindings:
            self._key_bindings[action] = []
        if key not in self._key_bindings[action]:
            self._key_bindings[action].append(key)
        self._rebuild_reverse_bindings()

    def unbind_key(self, action: Action, key: int) -> None:
        """Remove a key binding for an action."""
        if action in self._key_bindings:
            if key in self._key_bindings[action]:
                self._key_bindings[action].remove(key)
        self._rebuild_reverse_bindings()

    def clear_bindings(self, action: Action) -> None:
        """Clear all bindings for an action."""
        self._key_bindings[action] = []
        self._rebuild_reverse_bindings()

    def get_bindings(self, action: Action) -> list[int]:
        """Get all key bindings for an action."""
        return self._key_bindings.get(action, []).copy()

    # Text input

    def start_text_input(self, callback: Callable[[str], None]) -> None:
        """Start capturing text input."""
        self._text_input_callback = callback
        pygame.key.start_text_input()

    def stop_text_input(self) -> None:
        """Stop capturing text input."""
        self._text_input_callback = None
        pygame.key.stop_text_input()

    # Frame update

    def process_event(self, event: pygame.event.Event) -> None:
        """Process a pygame event."""
        if event.type == pygame.KEYDOWN:
            self._on_key_down(event.key)

        elif event.type == pygame.KEYUP:
            self._on_key_up(event.key)

        elif event.type == pygame.MOUSEMOTION:
            self._state.mouse.x = event.pos[0]
            self._state.mouse.y = event.pos[1]
            self._state.mouse.dx = event.rel[0]
            self._state.mouse.dy = event.rel[1]

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button <= 3:
                buttons = list(self._state.mouse.buttons)
                buttons[event.button - 1] = True
                self._state.mouse.buttons = tuple(buttons)  # type: ignore

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button <= 3:
                buttons = list(self._state.mouse.buttons)
                buttons[event.button - 1] = False
                self._state.mouse.buttons = tuple(buttons)  # type: ignore

        elif event.type == pygame.MOUSEWHEEL:
            self._state.mouse.wheel = event.y

        elif event.type == pygame.JOYDEVICEADDED:
            self._refresh_gamepads()

        elif event.type == pygame.JOYDEVICEREMOVED:
            self._refresh_gamepads()

        elif event.type == pygame.JOYBUTTONDOWN:
            self._on_gamepad_button_down(event.button)

        elif event.type == pygame.JOYBUTTONUP:
            self._on_gamepad_button_up(event.button)

        elif event.type == pygame.JOYAXISMOTION:
            self._state.axis_values[event.axis] = event.value
            self._process_axis_actions(event.axis, event.value)

        elif event.type == pygame.JOYHATMOTION:
            self._on_hat_motion(event.value)

        elif event.type == pygame.TEXTINPUT:
            if self._text_input_callback:
                self._text_input_callback(event.text)

    def update(self) -> None:
        """
        Update input state for new frame.

        Call this at the start of each fixed update.
        """
        # Calculate just pressed/released
        self._state.actions_just_pressed = self._state.actions_pressed - self._prev_actions
        self._state.actions_just_released = self._prev_actions - self._state.actions_pressed
        self._state.keys_just_pressed = self._state.keys_pressed - self._prev_keys
        self._state.keys_just_released = self._prev_keys - self._state.keys_pressed

        # Publish events
        if self.event_bus:
            for action in self._state.actions_just_pressed:
                self.event_bus.publish(InputEvent.ACTION_PRESSED, action=action)
            for action in self._state.actions_just_released:
                self.event_bus.publish(InputEvent.ACTION_RELEASED, action=action)

        # Save current state for next frame
        self._prev_actions = self._state.actions_pressed.copy()
        self._prev_keys = self._state.keys_pressed.copy()

        # Reset per-frame values
        self._state.mouse.dx = 0
        self._state.mouse.dy = 0
        self._state.mouse.wheel = 0

    def _on_key_down(self, key: int) -> None:
        """Handle key press."""
        self._state.keys_pressed.add(key)

        # Map to actions
        if key in self._reverse_key_bindings:
            for action in self._reverse_key_bindings[key]:
                self._state.actions_pressed.add(action)

    def _on_key_up(self, key: int) -> None:
        """Handle key release."""
        self._state.keys_pressed.discard(key)

        # Unmap from actions (only if no other keys for that action are pressed)
        if key in self._reverse_key_bindings:
            for action in self._reverse_key_bindings[key]:
                # Check if any other key for this action is still pressed
                still_pressed = False
                for other_key in self._key_bindings.get(action, []):
                    if other_key != key and other_key in self._state.keys_pressed:
                        still_pressed = True
                        break

                if not still_pressed:
                    self._state.actions_pressed.discard(action)

    def _on_gamepad_button_down(self, button: int) -> None:
        """Handle gamepad button press."""
        for action, buttons in self._gamepad_bindings.items():
            if button in buttons:
                self._state.actions_pressed.add(action)

    def _on_gamepad_button_up(self, button: int) -> None:
        """Handle gamepad button release."""
        for action, buttons in self._gamepad_bindings.items():
            if button in buttons:
                self._state.actions_pressed.discard(action)

    def _process_axis_actions(self, axis: int, value: float) -> None:
        """Process axis input into actions."""
        for ax, threshold, pos_action, neg_action in self._gamepad_axis_bindings:
            if ax == axis:
                if value > threshold:
                    self._state.actions_pressed.add(pos_action)
                    self._state.actions_pressed.discard(neg_action)
                elif value < -threshold:
                    self._state.actions_pressed.add(neg_action)
                    self._state.actions_pressed.discard(pos_action)
                else:
                    self._state.actions_pressed.discard(pos_action)
                    self._state.actions_pressed.discard(neg_action)

    def _on_hat_motion(self, value: tuple[int, int]) -> None:
        """Handle D-pad input."""
        # Clear all hat actions first
        for action in self._gamepad_hat_bindings.values():
            self._state.actions_pressed.discard(action)

        # Set active hat action
        if value in self._gamepad_hat_bindings:
            self._state.actions_pressed.add(self._gamepad_hat_bindings[value])
