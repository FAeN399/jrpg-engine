"""
Grid widget for 2D selection (inventory, equipment slots, etc).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Callable, Any, Tuple, Dict

from engine.ui.widget import Widget
from engine.ui.renderer import FontConfig

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


@dataclass
class GridCell:
    """Data for a grid cell."""
    icon: Optional[str] = None  # Icon/sprite path
    text: Optional[str] = None  # Small text (quantity, etc)
    value: Any = None
    enabled: bool = True
    data: Any = None  # Custom user data
    empty: bool = True  # True if slot is empty


class SelectableGrid(Widget):
    """
    2D grid selection widget.

    Features:
    - Keyboard/gamepad 2D navigation
    - Cell icons with quantity text
    - Custom cell rendering
    - Selection callback
    - Scroll support for large grids
    """

    def __init__(
        self,
        columns: int = 5,
        rows: int = 4,
        cell_size: float = 48,
    ):
        super().__init__()
        self._columns = columns
        self._rows = rows
        self._cell_size = cell_size
        self._cell_spacing = 4

        # Cell data
        self._cells: Dict[int, GridCell] = {}

        # Selection
        self._selected_col = 0
        self._selected_row = 0
        self._scroll_row = 0  # For vertical scrolling

        # Callbacks
        self.on_select: Optional[Callable[[int, int, GridCell], None]] = None
        self.on_selection_changed: Optional[Callable[[int, int], None]] = None

        # Visual options
        self.show_empty_cells: bool = True
        self.show_cell_border: bool = True

        # Focusable
        self.focusable = True

    # Properties

    @property
    def columns(self) -> int:
        return self._columns

    @property
    def rows(self) -> int:
        return self._rows

    @property
    def cell_size(self) -> float:
        return self._cell_size

    @property
    def selected_index(self) -> int:
        """Get selected cell as linear index."""
        return self._selected_row * self._columns + self._selected_col

    @property
    def selected_cell(self) -> Optional[GridCell]:
        """Get selected cell data."""
        return self._cells.get(self.selected_index)

    @property
    def selected_position(self) -> Tuple[int, int]:
        """Get selected (col, row)."""
        return (self._selected_col, self._selected_row)

    # Cell management

    def set_cell(
        self,
        index: int,
        icon: Optional[str] = None,
        text: Optional[str] = None,
        value: Any = None,
        enabled: bool = True,
    ) -> 'SelectableGrid':
        """Set cell data by linear index."""
        self._cells[index] = GridCell(
            icon=icon,
            text=text,
            value=value,
            enabled=enabled,
            empty=icon is None and text is None,
        )
        return self

    def set_cell_at(
        self,
        col: int,
        row: int,
        icon: Optional[str] = None,
        text: Optional[str] = None,
        value: Any = None,
        enabled: bool = True,
    ) -> 'SelectableGrid':
        """Set cell data by column and row."""
        index = row * self._columns + col
        return self.set_cell(index, icon, text, value, enabled)

    def get_cell(self, index: int) -> Optional[GridCell]:
        """Get cell data by index."""
        return self._cells.get(index)

    def get_cell_at(self, col: int, row: int) -> Optional[GridCell]:
        """Get cell data by position."""
        index = row * self._columns + col
        return self._cells.get(index)

    def clear_cell(self, index: int) -> None:
        """Clear a cell."""
        if index in self._cells:
            del self._cells[index]

    def clear(self) -> None:
        """Clear all cells."""
        self._cells.clear()

    def set_selection(self, col: int, row: int) -> None:
        """Set selection position."""
        old_col, old_row = self._selected_col, self._selected_row

        self._selected_col = max(0, min(col, self._columns - 1))
        self._selected_row = max(0, min(row, self._rows - 1))

        if (old_col, old_row) != (self._selected_col, self._selected_row):
            if self.on_selection_changed:
                self.on_selection_changed(self._selected_col, self._selected_row)

    # Navigation

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """Handle 2D navigation."""
        new_col = self._selected_col + col_delta
        new_row = self._selected_row + row_delta

        # Check bounds
        if new_col < 0 or new_col >= self._columns:
            return False
        if new_row < 0 or new_row >= self._rows:
            return False

        self.set_selection(new_col, new_row)
        return True

    def on_confirm(self) -> bool:
        """Handle cell selection."""
        cell = self.selected_cell
        index = self.selected_index

        # Can select empty cells or existing cells
        if cell and not cell.enabled:
            return False

        if self.on_select:
            # Create empty cell if needed for callback
            if cell is None:
                cell = GridCell(empty=True)
            self.on_select(self._selected_col, self._selected_row, cell)

        return True

    # Rendering

    def render(self, renderer: 'UIRenderer') -> None:
        """Render the grid."""
        x, y = self.absolute_position
        theme = self.theme
        spacing = theme.spacing

        total_cell = self._cell_size + self._cell_spacing

        # Update rect size if needed
        if self.rect.width == 0:
            self.rect.width = self._columns * total_cell - self._cell_spacing + self.padding.horizontal
        if self.rect.height == 0:
            self.rect.height = self._rows * total_cell - self._cell_spacing + self.padding.vertical

        # Background
        renderer.draw_rect(
            x, y, self.rect.width, self.rect.height,
            theme.colors.bg_primary
        )

        # Render cells
        content_x = x + self.padding.left
        content_y = y + self.padding.top

        for row in range(self._rows):
            for col in range(self._columns):
                cell_x = content_x + col * total_cell
                cell_y = content_y + row * total_cell
                index = row * self._columns + col
                cell = self._cells.get(index)

                is_selected = (col == self._selected_col and row == self._selected_row)

                self._render_cell(
                    renderer, cell_x, cell_y,
                    cell, is_selected
                )

        # Border
        renderer.draw_rect_outline(
            x, y, self.rect.width, self.rect.height,
            theme.colors.border_normal
        )

    def _render_cell(
        self,
        renderer: 'UIRenderer',
        x: float,
        y: float,
        cell: Optional[GridCell],
        is_selected: bool,
    ) -> None:
        """Render a single cell."""
        theme = self.theme
        size = self._cell_size

        # Determine colors
        if is_selected and self.focused:
            bg_color = theme.colors.bg_active
            border_color = theme.colors.border_active
        elif cell and not cell.empty:
            bg_color = theme.colors.bg_secondary
            border_color = theme.colors.border_normal
        elif self.show_empty_cells:
            bg_color = theme.colors.bg_tertiary
            border_color = theme.colors.border_normal
        else:
            return  # Don't render empty cells

        # Cell background
        renderer.draw_rect(x, y, size, size, bg_color)

        # Cell border
        if self.show_cell_border:
            renderer.draw_rect_outline(x, y, size, size, border_color)

        # Selection indicator
        if is_selected and self.focused:
            renderer.draw_rect_outline(
                x - 1, y - 1, size + 2, size + 2,
                theme.colors.focus_ring,
                thickness=2
            )

        # Cell content
        if cell and not cell.empty:
            # Icon
            if cell.icon:
                icon_padding = 4
                icon_size = size - icon_padding * 2
                renderer.draw_sprite(
                    cell.icon,
                    x + icon_padding, y + icon_padding,
                    icon_size, icon_size
                )

            # Quantity text (bottom right)
            if cell.text:
                font_config = FontConfig(
                    name=theme.fonts.family,
                    size=theme.fonts.size_small,
                    bold=True,
                )
                text_x = x + size - 4
                text_y = y + size - theme.fonts.size_small - 2

                # Shadow
                renderer.draw_text(
                    cell.text,
                    text_x + 1, text_y + 1,
                    color=(0, 0, 0),
                    font_config=font_config,
                    align="right"
                )
                # Text
                renderer.draw_text(
                    cell.text,
                    text_x, text_y,
                    color=theme.colors.text_primary,
                    font_config=font_config,
                    align="right"
                )

            # Disabled overlay
            if not cell.enabled:
                renderer.draw_rect(x, y, size, size, (0, 0, 0, 128))

    def get_preferred_size(self) -> Tuple[float, float]:
        """Get preferred size."""
        total_cell = self._cell_size + self._cell_spacing
        width = self._columns * total_cell - self._cell_spacing + self.padding.horizontal
        height = self._rows * total_cell - self._cell_spacing + self.padding.vertical
        return (width, height)
