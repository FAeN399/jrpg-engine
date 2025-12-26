"""
Grid layout - arranges children in a 2D grid.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Tuple, Optional

from engine.ui.layouts.layout import Layout, Alignment

if TYPE_CHECKING:
    from engine.ui.widget import Widget


class GridLayout(Layout):
    """
    Grid layout.

    Arranges children in a grid with specified columns.
    Rows are added automatically as needed.

    Usage:
        layout = GridLayout(columns=3)
        for i in range(9):
            layout.add_child(Button(f"Item {i}"))
    """

    def __init__(self, columns: int = 3):
        super().__init__()
        self._columns = columns
        self.spacing = 8
        self.row_spacing: Optional[float] = None  # None = use spacing

        # Cell sizing
        self.cell_width: Optional[float] = None  # None = auto
        self.cell_height: Optional[float] = None  # None = auto
        self.uniform_cells: bool = True  # All cells same size

        # Navigation tracking
        self._current_col = 0
        self._current_row = 0

    @property
    def columns(self) -> int:
        return self._columns

    @columns.setter
    def columns(self, value: int) -> None:
        self._columns = max(1, value)
        self.layout()

    @property
    def rows(self) -> int:
        """Calculate number of rows needed."""
        visible = len([c for c in self.children if c.visible])
        return (visible + self._columns - 1) // self._columns

    def set_columns(self, columns: int) -> 'GridLayout':
        """Set column count (fluent)."""
        self.columns = columns
        return self

    def set_cell_size(self, width: float, height: float) -> 'GridLayout':
        """Set uniform cell size (fluent)."""
        self.cell_width = width
        self.cell_height = height
        self.layout()
        return self

    def layout(self) -> None:
        """Position children in grid."""
        if not self.children:
            return

        visible_children = [c for c in self.children if c.visible]
        if not visible_children:
            return

        # Calculate cell dimensions
        row_gap = self.row_spacing if self.row_spacing is not None else self.spacing

        if self.uniform_cells:
            # Calculate uniform cell size
            if self.cell_width:
                cell_w = self.cell_width
            else:
                cell_w = max(c.rect.width + c.margin.horizontal for c in visible_children)

            if self.cell_height:
                cell_h = self.cell_height
            else:
                cell_h = max(c.rect.height + c.margin.vertical for c in visible_children)
        else:
            cell_w = cell_h = 0  # Will calculate per row/col

        # Position children
        content_x = self.padding.left
        content_y = self.padding.top

        for i, child in enumerate(visible_children):
            col = i % self._columns
            row = i // self._columns

            if self.uniform_cells:
                # Uniform grid
                x = content_x + col * (cell_w + self.spacing)
                y = content_y + row * (cell_h + row_gap)

                # Apply alignment within cell
                if self.cross_align == Alignment.CENTER:
                    x += (cell_w - child.rect.width - child.margin.horizontal) / 2
                    y += (cell_h - child.rect.height - child.margin.vertical) / 2
                elif self.cross_align == Alignment.END:
                    x += cell_w - child.rect.width - child.margin.horizontal
                    y += cell_h - child.rect.height - child.margin.vertical
                elif self.cross_align == Alignment.STRETCH:
                    child.rect.width = cell_w - child.margin.horizontal
                    child.rect.height = cell_h - child.margin.vertical

                child.rect.x = x + child.margin.left
                child.rect.y = y + child.margin.top
            else:
                # Non-uniform - simple flow layout
                x = content_x
                y = content_y

                for j in range(col):
                    prev_child = visible_children[row * self._columns + j]
                    x += prev_child.rect.width + prev_child.margin.horizontal + self.spacing

                for j in range(row):
                    # Get max height of previous row
                    row_start = j * self._columns
                    row_end = min(row_start + self._columns, len(visible_children))
                    max_h = max(
                        visible_children[k].rect.height + visible_children[k].margin.vertical
                        for k in range(row_start, row_end)
                    )
                    y += max_h + row_gap

                child.rect.x = x + child.margin.left
                child.rect.y = y + child.margin.top

            child.layout()

        # Fit content
        if self.fit_content:
            if self.uniform_cells:
                self.rect.width = self._columns * (cell_w + self.spacing) - self.spacing + self.padding.horizontal
                self.rect.height = self.rows * (cell_h + row_gap) - row_gap + self.padding.vertical

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """Handle 2D grid navigation."""
        focusable = self.focusable_children
        if not focusable:
            return False

        # Get current position
        current_index = self._focused_index
        current_col = current_index % self._columns
        current_row = current_index // self._columns

        # Calculate new position
        new_col = current_col + col_delta
        new_row = current_row + row_delta

        # Check bounds
        max_row = (len(focusable) - 1) // self._columns

        if new_col < 0 or new_col >= self._columns:
            return False
        if new_row < 0 or new_row > max_row:
            return False

        # Calculate new index
        new_index = new_row * self._columns + new_col

        if new_index >= len(focusable):
            return False

        return self.focus_child(new_index)

    def get_preferred_size(self) -> Tuple[float, float]:
        """Calculate preferred size."""
        visible = [c for c in self.children if c.visible]
        if not visible:
            return (self.padding.horizontal, self.padding.vertical)

        row_gap = self.row_spacing if self.row_spacing is not None else self.spacing

        if self.uniform_cells and self.cell_width and self.cell_height:
            width = self._columns * (self.cell_width + self.spacing) - self.spacing
            height = self.rows * (self.cell_height + row_gap) - row_gap
        else:
            cell_w = max(c.rect.width + c.margin.horizontal for c in visible)
            cell_h = max(c.rect.height + c.margin.vertical for c in visible)
            width = self._columns * (cell_w + self.spacing) - self.spacing
            height = self.rows * (cell_h + row_gap) - row_gap

        return (
            width + self.padding.horizontal,
            height + self.padding.vertical
        )

    def get_child_at_position(self, col: int, row: int) -> Optional['Widget']:
        """Get child at grid position."""
        index = row * self._columns + col
        visible = [c for c in self.children if c.visible]
        if 0 <= index < len(visible):
            return visible[index]
        return None
