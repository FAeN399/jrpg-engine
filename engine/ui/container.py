"""
Container widget for holding child widgets.

Containers manage child focus and navigation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Iterator

from engine.ui.widget import Widget

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


class Container(Widget):
    """
    Widget that contains child widgets.

    Provides:
    - Child management (add, remove, clear)
    - Focus navigation between children
    - Layout management (override in subclasses)
    - Recursive update/render
    """

    def __init__(self):
        super().__init__()
        self.children: List[Widget] = []
        self.focusable = True  # Containers can receive focus to manage children
        self._focused_index: int = 0
        self._wrap_navigation: bool = False  # Wrap around at ends

    # Child management

    def add_child(self, widget: Widget) -> 'Container':
        """
        Add a child widget.

        Args:
            widget: Widget to add

        Returns:
            Self for chaining
        """
        widget.parent = self
        widget.manager = self.manager
        self.children.append(widget)
        return self

    def add_children(self, *widgets: Widget) -> 'Container':
        """Add multiple children."""
        for widget in widgets:
            self.add_child(widget)
        return self

    def insert_child(self, index: int, widget: Widget) -> 'Container':
        """Insert a child at specific index."""
        widget.parent = self
        widget.manager = self.manager
        self.children.insert(index, widget)
        return self

    def remove_child(self, widget: Widget) -> bool:
        """
        Remove a child widget.

        Returns:
            True if widget was found and removed
        """
        if widget in self.children:
            widget.parent = None
            widget.manager = None
            self.children.remove(widget)
            return True
        return False

    def clear_children(self) -> None:
        """Remove all children."""
        for child in self.children:
            child.parent = None
            child.manager = None
        self.children.clear()
        self._focused_index = 0

    def get_child(self, index: int) -> Optional[Widget]:
        """Get child by index."""
        if 0 <= index < len(self.children):
            return self.children[index]
        return None

    def get_child_by_tag(self, tag: str) -> Optional[Widget]:
        """Get child by tag."""
        for child in self.children:
            if child.tag == tag:
                return child
        return None

    def child_count(self) -> int:
        """Get number of children."""
        return len(self.children)

    def iter_children(self, recursive: bool = False) -> Iterator[Widget]:
        """
        Iterate over children.

        Args:
            recursive: If True, also iterate over children's children
        """
        for child in self.children:
            yield child
            if recursive and isinstance(child, Container):
                yield from child.iter_children(recursive=True)

    # Focus management

    @property
    def focusable_children(self) -> List[Widget]:
        """Get all focusable visible enabled children."""
        return [
            c for c in self.children
            if c.focusable and c.enabled and c.visible
        ]

    @property
    def focused_child(self) -> Optional[Widget]:
        """Get currently focused child."""
        focusable = self.focusable_children
        if focusable and 0 <= self._focused_index < len(focusable):
            return focusable[self._focused_index]
        return None

    def focus_first(self) -> bool:
        """
        Focus the first focusable child.

        Returns:
            True if a child was focused
        """
        self._focused_index = 0
        focusable = self.focusable_children

        if focusable:
            return focusable[0].focus()
        return False

    def focus_last(self) -> bool:
        """Focus the last focusable child."""
        focusable = self.focusable_children

        if focusable:
            self._focused_index = len(focusable) - 1
            return focusable[-1].focus()
        return False

    def focus_child(self, index: int) -> bool:
        """
        Focus child at index.

        Args:
            index: Index into focusable children list

        Returns:
            True if focus changed
        """
        focusable = self.focusable_children
        if not focusable:
            return False

        # Clamp index
        index = max(0, min(index, len(focusable) - 1))

        if index == self._focused_index:
            return False

        # Unfocus current
        if self.focused_child:
            self.focused_child.unfocus()

        # Focus new
        self._focused_index = index
        return focusable[index].focus()

    def focus_next(self) -> bool:
        """Focus next focusable child."""
        focusable = self.focusable_children
        if not focusable:
            return False

        new_index = self._focused_index + 1

        if new_index >= len(focusable):
            if self._wrap_navigation:
                new_index = 0
            else:
                return False

        return self.focus_child(new_index)

    def focus_prev(self) -> bool:
        """Focus previous focusable child."""
        focusable = self.focusable_children
        if not focusable:
            return False

        new_index = self._focused_index - 1

        if new_index < 0:
            if self._wrap_navigation:
                new_index = len(focusable) - 1
            else:
                return False

        return self.focus_child(new_index)

    def focus_widget(self, widget: Widget) -> bool:
        """Focus a specific child widget."""
        focusable = self.focusable_children

        if widget in focusable:
            index = focusable.index(widget)
            return self.focus_child(index)
        return False

    # Input handling

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """
        Handle navigation between children.

        Default: vertical navigation (up/down changes focus).
        Override for custom navigation (e.g., grid layouts).
        """
        # First, let focused child handle navigation
        if self.focused_child:
            if self.focused_child.navigate(row_delta, col_delta):
                return True

        # Default: vertical navigation
        if row_delta < 0:
            return self.focus_prev()
        elif row_delta > 0:
            return self.focus_next()

        return False

    def on_confirm(self) -> bool:
        """Pass confirm to focused child."""
        if self.focused_child:
            return self.focused_child.on_confirm()
        return False

    def on_cancel(self) -> bool:
        """
        Handle cancel.

        Default: if this is a modal in UIManager, pop it.
        """
        if self.manager and self in self.manager.modal_stack:
            self.manager.pop_modal()
            return True
        return False

    # Manager propagation

    @property
    def manager(self):
        return getattr(self, '_manager', None)

    @manager.setter
    def manager(self, value):
        self._manager = value
        # Propagate to children (only if children exists)
        if hasattr(self, 'children'):
            for child in self.children:
                child.manager = value

    # Lifecycle

    def focus(self) -> bool:
        """Focus this container and its first child."""
        if super().focus():
            self.focus_first()
            return True
        return False

    def unfocus(self) -> None:
        """Unfocus this container and any focused child."""
        super().unfocus()
        if self.focused_child:
            self.focused_child.unfocus()

    def update(self, dt: float) -> None:
        """Update all visible children."""
        for child in self.children:
            if child.visible:
                child.update(dt)

    def render(self, renderer: 'UIRenderer') -> None:
        """Render all visible children."""
        for child in self.children:
            if child.visible:
                child.render(renderer)

    def layout(self) -> None:
        """
        Recalculate layout for children.

        Override in layout subclasses for specific behavior.
        """
        for child in self.children:
            child.layout()

    def get_preferred_size(self) -> tuple[float, float]:
        """Get size needed to contain all children."""
        if not self.children:
            return (self.padding.horizontal, self.padding.vertical)

        max_right = 0.0
        max_bottom = 0.0

        for child in self.children:
            if child.visible:
                right = child.rect.x + child.rect.width + child.margin.right
                bottom = child.rect.y + child.rect.height + child.margin.bottom
                max_right = max(max_right, right)
                max_bottom = max(max_bottom, bottom)

        return (
            max_right + self.padding.horizontal,
            max_bottom + self.padding.vertical
        )

    # Search

    def find_by_tag(self, tag: str) -> Optional[Widget]:
        """Find widget by tag (recursive)."""
        if self.tag == tag:
            return self

        for child in self.children:
            result = child.find_by_tag(tag)
            if result:
                return result

        return None
