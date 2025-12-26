"""
Base widget class for all UI elements.

Widgets are DATA + BEHAVIOR (unlike ECS components).
This is intentional - UI is inherently stateful.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Callable, Tuple

if TYPE_CHECKING:
    from engine.ui.manager import UIManager
    from engine.ui.container import Container
    from engine.ui.renderer import UIRenderer
    from engine.ui.theme import Theme


@dataclass
class Rect:
    """UI rectangle."""
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0

    def contains(self, px: float, py: float) -> bool:
        """Check if point is inside rect."""
        return (self.x <= px < self.x + self.width and
                self.y <= py < self.y + self.height)

    def intersects(self, other: 'Rect') -> bool:
        """Check if rectangles intersect."""
        return not (
            self.x + self.width <= other.x or
            other.x + other.width <= self.x or
            self.y + self.height <= other.y or
            other.y + other.height <= self.y
        )

    def copy(self) -> 'Rect':
        """Create a copy of this rect."""
        return Rect(self.x, self.y, self.width, self.height)


@dataclass
class Padding:
    """Padding values."""
    top: float = 0
    right: float = 0
    bottom: float = 0
    left: float = 0

    @classmethod
    def all(cls, value: float) -> 'Padding':
        """Create uniform padding."""
        return cls(value, value, value, value)

    @classmethod
    def symmetric(cls, horizontal: float, vertical: float) -> 'Padding':
        """Create symmetric padding."""
        return cls(vertical, horizontal, vertical, horizontal)

    @property
    def horizontal(self) -> float:
        """Total horizontal padding."""
        return self.left + self.right

    @property
    def vertical(self) -> float:
        """Total vertical padding."""
        return self.top + self.bottom


@dataclass
class Margin:
    """Margin values."""
    top: float = 0
    right: float = 0
    bottom: float = 0
    left: float = 0

    @classmethod
    def all(cls, value: float) -> 'Margin':
        """Create uniform margin."""
        return cls(value, value, value, value)


class Widget(ABC):
    """
    Base class for all UI widgets.

    Widgets have both data and behavior, unlike ECS components.
    They can be focused, receive input, and render themselves.
    """

    def __init__(self):
        # Geometry
        self.rect = Rect()
        self.padding = Padding()
        self.margin = Margin()
        self.min_width: float = 0
        self.min_height: float = 0
        self.max_width: float = float('inf')
        self.max_height: float = float('inf')

        # State
        self.visible: bool = True
        self.enabled: bool = True
        self.focusable: bool = False
        self.focused: bool = False

        # Hierarchy
        self.parent: Optional[Container] = None
        self.manager: Optional[UIManager] = None
        self.tag: str = ""  # For identification

        # Callbacks
        self.on_focus_enter: Optional[Callable[[], None]] = None
        self.on_focus_exit: Optional[Callable[[], None]] = None

        # Theme override (uses manager theme if None)
        self._theme: Optional[Theme] = None

    @property
    def theme(self) -> 'Theme':
        """Get the active theme."""
        if self._theme:
            return self._theme
        if self.manager:
            return self.manager.theme
        # Import here to avoid circular import
        from engine.ui.theme import DEFAULT_THEME
        return DEFAULT_THEME

    @theme.setter
    def theme(self, value: Optional['Theme']) -> None:
        """Set theme override."""
        self._theme = value

    @property
    def absolute_position(self) -> Tuple[float, float]:
        """Get absolute screen position."""
        if self.parent:
            px, py = self.parent.content_position
            return (px + self.rect.x, py + self.rect.y)
        return (self.rect.x, self.rect.y)

    @property
    def absolute_rect(self) -> Rect:
        """Get rect in absolute screen coordinates."""
        x, y = self.absolute_position
        return Rect(x, y, self.rect.width, self.rect.height)

    @property
    def content_rect(self) -> Rect:
        """Get rect excluding padding."""
        return Rect(
            self.rect.x + self.padding.left,
            self.rect.y + self.padding.top,
            self.rect.width - self.padding.horizontal,
            self.rect.height - self.padding.vertical,
        )

    @property
    def content_position(self) -> Tuple[float, float]:
        """Get absolute position of content area."""
        x, y = self.absolute_position
        return (x + self.padding.left, y + self.padding.top)

    # Fluent setters

    def set_position(self, x: float, y: float) -> 'Widget':
        """Set position (fluent)."""
        self.rect.x = x
        self.rect.y = y
        return self

    def set_size(self, width: float, height: float) -> 'Widget':
        """Set size (fluent)."""
        self.rect.width = max(self.min_width, min(width, self.max_width))
        self.rect.height = max(self.min_height, min(height, self.max_height))
        return self

    def set_padding(self, padding: Padding) -> 'Widget':
        """Set padding (fluent)."""
        self.padding = padding
        return self

    def set_margin(self, margin: Margin) -> 'Widget':
        """Set margin (fluent)."""
        self.margin = margin
        return self

    def set_visible(self, visible: bool) -> 'Widget':
        """Set visibility (fluent)."""
        self.visible = visible
        return self

    def set_enabled(self, enabled: bool) -> 'Widget':
        """Set enabled state (fluent)."""
        self.enabled = enabled
        if not enabled:
            self.unfocus()
        return self

    def set_tag(self, tag: str) -> 'Widget':
        """Set tag for identification (fluent)."""
        self.tag = tag
        return self

    # Focus management

    def focus(self) -> bool:
        """
        Request focus for this widget.

        Returns:
            True if focus was granted
        """
        if not self.focusable or not self.enabled or not self.visible:
            return False

        self.focused = True

        if self.on_focus_enter:
            self.on_focus_enter()

        return True

    def unfocus(self) -> None:
        """Remove focus from this widget."""
        if not self.focused:
            return

        self.focused = False

        if self.on_focus_exit:
            self.on_focus_exit()

    # Input handling (override in subclasses)

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """
        Handle navigation input.

        Args:
            row_delta: Vertical direction (-1=up, 1=down)
            col_delta: Horizontal direction (-1=left, 1=right)

        Returns:
            True if navigation was handled
        """
        return False

    def on_confirm(self) -> bool:
        """
        Handle confirm/select input.

        Returns:
            True if input was handled
        """
        return False

    def on_cancel(self) -> bool:
        """
        Handle cancel/back input.

        Returns:
            True if input was handled
        """
        return False

    def on_mouse_enter(self) -> None:
        """Handle mouse entering widget."""
        pass

    def on_mouse_exit(self) -> None:
        """Handle mouse leaving widget."""
        pass

    def on_mouse_down(self, x: float, y: float, button: int) -> bool:
        """
        Handle mouse button press.

        Returns:
            True if input was handled
        """
        return False

    def on_mouse_up(self, x: float, y: float, button: int) -> bool:
        """
        Handle mouse button release.

        Returns:
            True if input was handled
        """
        return False

    # Lifecycle

    def update(self, dt: float) -> None:
        """
        Update widget state.

        Override for animations and time-based behavior.

        Args:
            dt: Delta time in seconds
        """
        pass

    @abstractmethod
    def render(self, renderer: 'UIRenderer') -> None:
        """
        Render the widget.

        Args:
            renderer: UI renderer to draw with
        """
        pass

    def layout(self) -> None:
        """
        Recalculate layout.

        Override for custom layout behavior.
        Called when parent size changes.
        """
        pass

    def get_preferred_size(self) -> Tuple[float, float]:
        """
        Get preferred size for layout.

        Returns:
            (width, height) tuple
        """
        return (self.rect.width, self.rect.height)

    # Utility

    def find_by_tag(self, tag: str) -> Optional['Widget']:
        """Find widget by tag (self only for base Widget)."""
        return self if self.tag == tag else None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(tag={self.tag!r}, pos=({self.rect.x}, {self.rect.y}))"
