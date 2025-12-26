"""
Inventory screen preset - Item management UI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable, List, Any
from dataclasses import dataclass

from engine.ui.container import Container
from engine.ui.widgets.label import Label
from engine.ui.widgets.panel import Panel
from engine.ui.widgets.grid import SelectableGrid, GridCell
from engine.ui.widgets.button import Button
from engine.ui.layouts.horizontal import HBoxLayout
from engine.ui.layouts.vertical import VBoxLayout
from engine.ui.widget import Padding

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


@dataclass
class InventoryItem:
    """Data for an inventory item."""
    id: str
    name: str
    description: str = ""
    icon: Optional[str] = None
    quantity: int = 1
    usable: bool = True
    category: str = "Items"  # All, Weapons, Armor, Items, Key Items
    data: Any = None


class InventoryScreen(Container):
    """
    Full-screen inventory management UI.

    Layout:
    ┌─────────────────────────────────────┐
    │ INVENTORY                    Gold: X │
    ├──────────────────┬──────────────────┤
    │                  │                   │
    │   Item Grid      │   Item Details    │
    │   (selectable)   │   - Name          │
    │                  │   - Description   │
    │                  │   - Stats         │
    │                  │   [Use] [Drop]    │
    │                  │                   │
    ├──────────────────┴──────────────────┤
    │ Category: All | Weapons | Armor      │
    └─────────────────────────────────────┘
    """

    def __init__(self, columns: int = 6, rows: int = 5):
        super().__init__()

        self._columns = columns
        self._rows = rows
        self._items: List[InventoryItem] = []
        self._selected_item: Optional[InventoryItem] = None
        self._gold = 0

        # Callbacks
        self.on_use: Optional[Callable[[InventoryItem], None]] = None
        self.on_drop: Optional[Callable[[InventoryItem], None]] = None
        self.on_close: Optional[Callable[[], None]] = None

        # Category filter
        self._categories = ["All", "Weapons", "Armor", "Items", "Key Items"]
        self._current_category = 0

        # Build UI
        self._build_ui()

        # Focusable
        self.focusable = True

    def _build_ui(self) -> None:
        """Build the inventory UI."""
        self.clear_children()
        theme = self.theme

        # Main panel
        self._main_panel = Panel()
        self._main_panel.set_title("INVENTORY")
        self._main_panel.show_shadow = True
        self._main_panel.padding = Padding.all(8)
        self.add_child(self._main_panel)

        # Content layout (horizontal: grid | details)
        self._content_layout = HBoxLayout()
        self._content_layout.spacing = 16
        self._content_layout.set_position(8, 40)
        self._main_panel.add_child(self._content_layout)

        # Left side: Item grid
        self._grid_panel = Panel()
        self._grid_panel.show_border = False
        self._grid_panel.show_background = False
        self._content_layout.add_child(self._grid_panel)

        self._item_grid = SelectableGrid(self._columns, self._rows, 48)
        self._item_grid.on_select = self._on_grid_select
        self._item_grid.on_selection_changed = self._on_selection_changed
        self._grid_panel.add_child(self._item_grid)

        # Right side: Details panel
        self._details_panel = Panel()
        self._details_panel.rect.width = 200
        self._details_panel.rect.height = self._rows * 52
        self._details_panel.padding = Padding.all(8)
        self._content_layout.add_child(self._details_panel)

        # Details content
        self._details_layout = VBoxLayout()
        self._details_layout.spacing = 8
        self._details_panel.add_child(self._details_layout)

        self._item_name_label = Label("")
        self._item_name_label._font_size = 18
        self._details_layout.add_child(self._item_name_label)

        self._item_desc_label = Label("")
        self._item_desc_label.max_width = 180
        self._details_layout.add_child(self._item_desc_label)

        # Action buttons
        self._button_layout = HBoxLayout()
        self._button_layout.spacing = 8

        self._use_btn = Button("Use")
        self._use_btn.rect.width = 80
        self._use_btn.set_on_click(self._on_use_clicked)
        self._button_layout.add_child(self._use_btn)

        self._drop_btn = Button("Drop")
        self._drop_btn.rect.width = 80
        self._drop_btn.set_on_click(self._on_drop_clicked)
        self._button_layout.add_child(self._drop_btn)

        self._details_layout.add_child(self._button_layout)

        # Gold label (top right)
        self._gold_label = Label(f"Gold: {self._gold}")
        self._gold_label.set_position(self._main_panel.rect.width - 100, 8)
        self._main_panel.add_child(self._gold_label)

        # Category tabs (bottom)
        self._category_layout = HBoxLayout()
        self._category_layout.spacing = 4
        self._category_layout.set_position(8, self._main_panel.rect.height - 40)

        for i, cat in enumerate(self._categories):
            cat_btn = Button(cat)
            cat_btn.rect.width = 80
            cat_btn.rect.height = 28
            cat_btn.set_on_click(lambda idx=i: self._set_category(idx))
            self._category_layout.add_child(cat_btn)

        self._main_panel.add_child(self._category_layout)

        # Initial sizing
        grid_w, grid_h = self._item_grid.get_preferred_size()
        self._grid_panel.rect.width = grid_w + 16
        self._grid_panel.rect.height = grid_h + 16

        self._main_panel.rect.width = grid_w + 200 + 64
        self._main_panel.rect.height = grid_h + 100

    def set_items(self, items: List[InventoryItem]) -> 'InventoryScreen':
        """Set inventory items."""
        self._items = items
        self._refresh_grid()
        return self

    def add_item(self, item: InventoryItem) -> 'InventoryScreen':
        """Add an item to inventory."""
        self._items.append(item)
        self._refresh_grid()
        return self

    def set_gold(self, amount: int) -> 'InventoryScreen':
        """Set gold amount."""
        self._gold = amount
        self._gold_label.text = f"Gold: {amount}"
        return self

    def _refresh_grid(self) -> None:
        """Refresh grid from items list (respecting category filter)."""
        self._item_grid.clear()

        # Filter items by current category
        filtered = self._get_filtered_items()

        for i, item in enumerate(filtered):
            qty_text = str(item.quantity) if item.quantity > 1 else ""
            self._item_grid.set_cell(i, item.icon, qty_text, item, item.usable)

    def _get_filtered_items(self) -> List[InventoryItem]:
        """Get items filtered by current category."""
        category = self._categories[self._current_category]

        if category == "All":
            return self._items

        return [item for item in self._items if item.category == category]

    def _on_grid_select(self, col: int, row: int, cell: GridCell) -> None:
        """Handle item selection (confirm)."""
        if cell and cell.value and cell.value.usable:
            self._on_use_clicked()

    def _on_selection_changed(self, col: int, row: int) -> None:
        """Handle selection cursor moved."""
        index = row * self._columns + col
        filtered = self._get_filtered_items()
        if 0 <= index < len(filtered):
            self._selected_item = filtered[index]
            self._update_details()
        else:
            self._selected_item = None
            self._clear_details()

    def _update_details(self) -> None:
        """Update details panel for selected item."""
        if self._selected_item:
            self._item_name_label.text = self._selected_item.name
            self._item_desc_label.text = self._selected_item.description
            self._use_btn.enabled = self._selected_item.usable

    def _clear_details(self) -> None:
        """Clear details panel."""
        self._item_name_label.text = ""
        self._item_desc_label.text = ""

    def _on_use_clicked(self) -> None:
        """Handle use button click."""
        if self._selected_item and self._selected_item.usable:
            if self.on_use:
                self.on_use(self._selected_item)

    def _on_drop_clicked(self) -> None:
        """Handle drop button click."""
        if self._selected_item:
            if self.on_drop:
                self.on_drop(self._selected_item)

    def _set_category(self, index: int) -> None:
        """Set category filter."""
        self._current_category = index
        self._selected_item = None
        self._clear_details()
        self._refresh_grid()

    # Input

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """Navigate the grid."""
        return self._item_grid.navigate(row_delta, col_delta)

    def on_confirm(self) -> bool:
        """Confirm selection."""
        return self._item_grid.on_confirm()

    def on_cancel(self) -> bool:
        """Close inventory."""
        if self.on_close:
            self.on_close()
        if self.manager:
            self.manager.pop_modal()
        return True

    def focus(self) -> bool:
        """Focus the grid."""
        if super().focus():
            self._item_grid.focus()
            return True
        return False

    def layout(self) -> None:
        """Center panel."""
        if self._main_panel:
            self._main_panel.rect.x = (self.rect.width - self._main_panel.rect.width) / 2
            self._main_panel.rect.y = (self.rect.height - self._main_panel.rect.height) / 2
        super().layout()

    # Rendering

    def render(self, renderer: 'UIRenderer') -> None:
        """Render inventory screen."""
        x, y = self.absolute_position

        # Dim background
        renderer.draw_rect(x, y, self.rect.width, self.rect.height, (0, 0, 0, 180))

        # Render children
        super().render(renderer)
