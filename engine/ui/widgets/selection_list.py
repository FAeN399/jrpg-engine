"""
Selection list widget for scrollable item selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Callable, List, Any, Tuple

from engine.ui.container import Container
from engine.ui.renderer import FontConfig

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


@dataclass
class ListItem:
    """Data for a list item."""
    text: str
    value: Any = None
    icon: Optional[str] = None
    enabled: bool = True
    data: Any = None  # Custom user data


class SelectionList(Container):
    """
    Scrollable selection list widget.

    Features:
    - Keyboard/gamepad navigation
    - Scrolling for long lists
    - Custom item rendering
    - Selection callback
    - Multi-select option
    """

    def __init__(self):
        super().__init__()
        self._items: List[ListItem] = []
        self._selected_index: int = 0
        self._scroll_offset: int = 0
        self._visible_count: int = 6

        # Selection mode
        self.multi_select: bool = False
        self._selected_indices: set[int] = set()

        # Callbacks
        self.on_select: Optional[Callable[[int, ListItem], None]] = None
        self.on_selection_changed: Optional[Callable[[int], None]] = None

        # Visual options
        self.show_scroll_bar: bool = True
        self.show_selection_indicator: bool = True
        self.item_height: Optional[float] = None  # None = use theme

        # Focusable
        self.focusable = True
        self._wrap_navigation = True  # Wrap at ends

    # Item management

    @property
    def items(self) -> List[ListItem]:
        """Get all items."""
        return self._items

    @property
    def selected_index(self) -> int:
        """Get selected item index."""
        return self._selected_index

    @selected_index.setter
    def selected_index(self, value: int) -> None:
        """Set selected item index."""
        if 0 <= value < len(self._items):
            old_index = self._selected_index
            self._selected_index = value
            self._ensure_visible(value)

            if old_index != value and self.on_selection_changed:
                self.on_selection_changed(value)

    @property
    def selected_item(self) -> Optional[ListItem]:
        """Get selected item."""
        if 0 <= self._selected_index < len(self._items):
            return self._items[self._selected_index]
        return None

    @property
    def selected_items(self) -> List[ListItem]:
        """Get all selected items (for multi-select)."""
        return [self._items[i] for i in sorted(self._selected_indices)]

    def add_item(
        self,
        text: str,
        value: Any = None,
        icon: Optional[str] = None,
        enabled: bool = True,
    ) -> 'SelectionList':
        """Add an item to the list."""
        item = ListItem(text=text, value=value, icon=icon, enabled=enabled)
        self._items.append(item)
        return self

    def add_items(self, *texts: str) -> 'SelectionList':
        """Add multiple text items."""
        for text in texts:
            self.add_item(text)
        return self

    def insert_item(self, index: int, item: ListItem) -> 'SelectionList':
        """Insert item at index."""
        self._items.insert(index, item)
        return self

    def remove_item(self, index: int) -> Optional[ListItem]:
        """Remove item at index."""
        if 0 <= index < len(self._items):
            item = self._items.pop(index)

            # Adjust selection
            if self._selected_index >= len(self._items):
                self._selected_index = max(0, len(self._items) - 1)

            return item
        return None

    def clear_items(self) -> None:
        """Remove all items."""
        self._items.clear()
        self._selected_index = 0
        self._scroll_offset = 0
        self._selected_indices.clear()

    def get_item(self, index: int) -> Optional[ListItem]:
        """Get item at index."""
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def find_item(self, value: Any) -> int:
        """Find item index by value. Returns -1 if not found."""
        for i, item in enumerate(self._items):
            if item.value == value:
                return i
        return -1

    def set_visible_count(self, count: int) -> 'SelectionList':
        """Set number of visible items."""
        self._visible_count = max(1, count)
        return self

    # Navigation

    def select_next(self) -> bool:
        """Select next item."""
        return self._navigate(1)

    def select_prev(self) -> bool:
        """Select previous item."""
        return self._navigate(-1)

    def _navigate(self, delta: int) -> bool:
        """Navigate by delta."""
        if not self._items:
            return False

        new_index = self._selected_index + delta

        # Wrap navigation
        if self._wrap_navigation:
            new_index = new_index % len(self._items)
        else:
            if new_index < 0 or new_index >= len(self._items):
                return False

        # Skip disabled items
        start_index = new_index
        while not self._items[new_index].enabled:
            new_index = (new_index + delta) % len(self._items)
            if new_index == start_index:
                return False  # All items disabled

        self.selected_index = new_index
        return True

    def _ensure_visible(self, index: int) -> None:
        """Scroll to ensure index is visible."""
        if index < self._scroll_offset:
            self._scroll_offset = index
        elif index >= self._scroll_offset + self._visible_count:
            self._scroll_offset = index - self._visible_count + 1

    # Input handling

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """Handle navigation."""
        if row_delta != 0:
            return self._navigate(row_delta)
        return False

    def on_confirm(self) -> bool:
        """Handle item selection."""
        if not self._items or not self.selected_item:
            return False

        item = self.selected_item
        if not item.enabled:
            return False

        # Toggle selection for multi-select
        if self.multi_select:
            if self._selected_index in self._selected_indices:
                self._selected_indices.remove(self._selected_index)
            else:
                self._selected_indices.add(self._selected_index)

        # Callback
        if self.on_select:
            self.on_select(self._selected_index, item)

        return True

    # Rendering

    def render(self, renderer: 'UIRenderer') -> None:
        """Render the list."""
        x, y = self.absolute_position
        theme = self.theme
        spacing = theme.spacing

        item_h = self.item_height or spacing.list_item_height
        visible_height = self._visible_count * item_h

        # Update rect height if needed
        if self.rect.height == 0:
            self.rect.height = visible_height + self.padding.vertical

        # Background
        renderer.draw_rect(
            x, y, self.rect.width, self.rect.height,
            theme.colors.bg_primary
        )

        # Border
        renderer.draw_rect_outline(
            x, y, self.rect.width, self.rect.height,
            theme.colors.border_normal
        )

        # Set clip region
        content_x = x + self.padding.left
        content_y = y + self.padding.top
        content_width = self.rect.width - self.padding.horizontal
        content_height = self.rect.height - self.padding.vertical

        if self.show_scroll_bar and len(self._items) > self._visible_count:
            content_width -= 12  # Reserve space for scrollbar

        renderer.set_clip(content_x, content_y, content_width, content_height)

        # Render visible items
        font_config = FontConfig(
            name=theme.fonts.family,
            size=theme.fonts.size_normal,
        )

        for i in range(self._visible_count):
            item_index = self._scroll_offset + i
            if item_index >= len(self._items):
                break

            item = self._items[item_index]
            item_y = content_y + i * item_h

            # Item background
            is_selected = item_index == self._selected_index
            is_multi_selected = item_index in self._selected_indices

            if is_selected and self.focused:
                renderer.draw_rect(
                    content_x, item_y, content_width, item_h,
                    theme.colors.bg_active
                )
            elif is_multi_selected:
                renderer.draw_rect(
                    content_x, item_y, content_width, item_h,
                    theme.colors.bg_hover
                )

            # Selection indicator
            if self.show_selection_indicator and is_selected and self.focused:
                indicator_x = content_x + 4
                indicator_y = item_y + item_h / 2
                renderer.draw_text(
                    ">",
                    indicator_x,
                    item_y + (item_h - theme.fonts.size_normal) / 2,
                    color=theme.colors.text_accent,
                    font_config=font_config
                )

            # Icon
            text_x = content_x + spacing.padding_md
            if self.show_selection_indicator:
                text_x += spacing.padding_md

            if item.icon:
                icon_size = spacing.icon_size
                icon_y = item_y + (item_h - icon_size) / 2
                renderer.draw_sprite(item.icon, text_x, icon_y, icon_size, icon_size)
                text_x += icon_size + spacing.padding_sm

            # Text
            text_color = theme.colors.text_primary if item.enabled else theme.colors.text_disabled
            if is_multi_selected:
                text_color = theme.colors.text_accent

            renderer.draw_text(
                item.text,
                text_x,
                item_y + (item_h - theme.fonts.size_normal) / 2,
                color=text_color,
                font_config=font_config
            )

        renderer.clear_clip()

        # Scroll bar
        if self.show_scroll_bar and len(self._items) > self._visible_count:
            self._render_scrollbar(renderer, x, y)

    def _render_scrollbar(self, renderer: 'UIRenderer', x: float, y: float) -> None:
        """Render the scrollbar."""
        theme = self.theme

        bar_x = x + self.rect.width - 10 - self.padding.right
        bar_y = y + self.padding.top
        bar_width = 8
        bar_height = self.rect.height - self.padding.vertical

        # Track
        renderer.draw_rect(bar_x, bar_y, bar_width, bar_height, theme.colors.bg_tertiary)

        # Thumb
        if len(self._items) > 0:
            thumb_height = max(20, bar_height * self._visible_count / len(self._items))
            thumb_y = bar_y + (bar_height - thumb_height) * self._scroll_offset / max(1, len(self._items) - self._visible_count)

            renderer.draw_rect(bar_x, thumb_y, bar_width, thumb_height, theme.colors.border_focus)

    def get_preferred_size(self) -> Tuple[float, float]:
        """Get preferred size."""
        theme = self.theme
        item_h = self.item_height or theme.spacing.list_item_height

        # Calculate width from longest item
        max_width = 100  # Minimum width
        for item in self._items:
            char_width = theme.fonts.size_normal * 0.6
            item_width = len(item.text) * char_width + theme.spacing.padding_md * 2
            if item.icon:
                item_width += theme.spacing.icon_size + theme.spacing.padding_sm
            max_width = max(max_width, item_width)

        height = min(len(self._items), self._visible_count) * item_h

        return (
            max_width + self.padding.horizontal + (12 if self.show_scroll_bar else 0),
            height + self.padding.vertical
        )
