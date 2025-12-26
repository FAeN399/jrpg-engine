"""
Focus management system for UI navigation.

Handles focus stack for modal dialogs and nested focus contexts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Callable
from enum import Enum, auto

if TYPE_CHECKING:
    from engine.ui.widget import Widget
    from engine.ui.container import Container


class FocusDirection(Enum):
    """Direction for focus navigation."""
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    NEXT = auto()     # Tab forward
    PREV = auto()     # Tab backward


class FocusManager:
    """
    Manages focus state across the UI system.

    Provides:
    - Focus stack for modal dialogs
    - Focus history for back navigation
    - Focus trapping within containers
    """

    def __init__(self):
        # Stack of focus contexts (for modals)
        self._context_stack: List[FocusContext] = []

        # Currently focused widget (across all contexts)
        self._focused: Optional[Widget] = None

        # Callbacks
        self.on_focus_changed: Optional[Callable[[Optional[Widget], Optional[Widget]], None]] = None

    @property
    def focused(self) -> Optional[Widget]:
        """Get currently focused widget."""
        return self._focused

    @property
    def current_context(self) -> Optional['FocusContext']:
        """Get current focus context."""
        return self._context_stack[-1] if self._context_stack else None

    def set_focus(self, widget: Optional[Widget]) -> bool:
        """
        Set focus to a widget.

        Args:
            widget: Widget to focus, or None to clear focus

        Returns:
            True if focus changed
        """
        if widget == self._focused:
            return False

        old_focus = self._focused

        # Unfocus old widget
        if self._focused:
            self._focused.unfocus()

        # Focus new widget
        self._focused = widget
        if widget:
            widget.focus()

        # Notify
        if self.on_focus_changed:
            self.on_focus_changed(old_focus, widget)

        return True

    def clear_focus(self) -> None:
        """Clear all focus."""
        self.set_focus(None)

    def push_context(self, root: 'Container', trap_focus: bool = True) -> 'FocusContext':
        """
        Push a new focus context (e.g., for a modal dialog).

        Args:
            root: Root container for the context
            trap_focus: If True, focus cannot leave this context

        Returns:
            The new focus context
        """
        context = FocusContext(root, trap_focus)
        self._context_stack.append(context)

        # Focus first widget in new context
        root.focus_first()

        return context

    def pop_context(self) -> Optional['FocusContext']:
        """
        Pop the current focus context.

        Returns:
            The popped context, or None if stack was empty
        """
        if not self._context_stack:
            return None

        context = self._context_stack.pop()

        # Unfocus any widget in the popped context
        if self._focused and self._is_descendant(self._focused, context.root):
            self._focused.unfocus()
            self._focused = None

        # Restore focus to previous context
        if self._context_stack:
            prev_context = self._context_stack[-1]
            if prev_context.last_focused:
                self.set_focus(prev_context.last_focused)
            else:
                prev_context.root.focus_first()

        return context

    def navigate(self, direction: FocusDirection) -> bool:
        """
        Navigate focus in a direction.

        Returns:
            True if focus moved
        """
        if not self._focused:
            return False

        row_delta = 0
        col_delta = 0

        if direction == FocusDirection.UP:
            row_delta = -1
        elif direction == FocusDirection.DOWN:
            row_delta = 1
        elif direction == FocusDirection.LEFT:
            col_delta = -1
        elif direction == FocusDirection.RIGHT:
            col_delta = 1
        elif direction == FocusDirection.NEXT:
            row_delta = 1  # Default: down = next
        elif direction == FocusDirection.PREV:
            row_delta = -1  # Default: up = prev

        return self._focused.navigate(row_delta, col_delta)

    def _is_descendant(self, widget: Widget, container: 'Container') -> bool:
        """Check if widget is a descendant of container."""
        current = widget.parent
        while current:
            if current == container:
                return True
            current = current.parent
        return False


class FocusContext:
    """
    A focus context for modal dialogs or screens.

    Tracks focus state within a container hierarchy.
    """

    def __init__(self, root: 'Container', trap_focus: bool = True):
        self.root = root
        self.trap_focus = trap_focus
        self.last_focused: Optional[Widget] = None
        self._focus_history: List[Widget] = []

    def record_focus(self, widget: Widget) -> None:
        """Record a focus event in history."""
        self.last_focused = widget

        # Avoid duplicates at end of history
        if not self._focus_history or self._focus_history[-1] != widget:
            self._focus_history.append(widget)

            # Limit history size
            if len(self._focus_history) > 50:
                self._focus_history = self._focus_history[-25:]

    def restore_previous(self) -> Optional[Widget]:
        """Get previous focused widget from history."""
        if len(self._focus_history) > 1:
            self._focus_history.pop()  # Remove current
            return self._focus_history[-1]
        return None


class FocusGroup:
    """
    A group of widgets that can be navigated as a unit.

    Useful for:
    - Tab groups
    - Radio button groups
    - Toolbar sections
    """

    def __init__(self, name: str = ""):
        self.name = name
        self.widgets: List[Widget] = []
        self._current_index: int = 0

    def add(self, widget: Widget) -> None:
        """Add widget to group."""
        if widget not in self.widgets:
            self.widgets.append(widget)

    def remove(self, widget: Widget) -> None:
        """Remove widget from group."""
        if widget in self.widgets:
            self.widgets.remove(widget)

    @property
    def current(self) -> Optional[Widget]:
        """Get current widget in group."""
        if self.widgets and 0 <= self._current_index < len(self.widgets):
            return self.widgets[self._current_index]
        return None

    def next(self) -> Optional[Widget]:
        """Move to next widget in group."""
        if not self.widgets:
            return None

        self._current_index = (self._current_index + 1) % len(self.widgets)
        return self.current

    def prev(self) -> Optional[Widget]:
        """Move to previous widget in group."""
        if not self.widgets:
            return None

        self._current_index = (self._current_index - 1) % len(self.widgets)
        return self.current

    def focus_current(self) -> bool:
        """Focus current widget in group."""
        if self.current:
            return self.current.focus()
        return False
