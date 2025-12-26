"""
Shop screen preset - Buy/sell interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable, List
from dataclasses import dataclass

from engine.ui.container import Container
from engine.ui.widgets.label import Label
from engine.ui.widgets.panel import Panel
from engine.ui.widgets.button import Button
from engine.ui.widgets.selection_list import SelectionList, ListItem
from engine.ui.layouts.vertical import VBoxLayout
from engine.ui.layouts.horizontal import HBoxLayout
from engine.ui.widget import Padding

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


@dataclass
class ShopItem:
    """Item available in shop."""
    id: str
    name: str
    price: int
    description: str = ""
    icon: Optional[str] = None
    stock: int = -1  # -1 = unlimited
    owned: int = 0  # For display


class ShopScreen(Container):
    """
    Shop buy/sell interface.

    Layout:
    ┌─────────────────────────────────────────┐
    │ SHOP - [Shop Name]          Gold: 1000  │
    ├─────────────────────────────────────────┤
    │  ┌─────────┐                            │
    │  │  Buy    │                            │
    │  │  Sell   │                            │
    │  │  Leave  │                            │
    │  └─────────┘                            │
    ├─────────────────────────────────────────┤
    │  Item List           │  Item Details    │
    │  Potion       50g    │  [Name]          │
    │  Antidote     30g    │  [Description]   │
    │  Tent        200g    │                  │
    │                      │  Owned: 5        │
    │                      │  [Buy] [x1/x10]  │
    └─────────────────────────────────────────┘
    """

    def __init__(self, shop_name: str = "Shop"):
        super().__init__()

        self._shop_name = shop_name
        self._gold = 0
        self._buy_items: List[ShopItem] = []
        self._sell_items: List[ShopItem] = []

        # State
        self._mode = "menu"  # "menu", "buy", "sell"
        self._selected_item: Optional[ShopItem] = None
        self._quantity = 1

        # Callbacks
        self.on_buy: Optional[Callable[[ShopItem, int], bool]] = None
        self.on_sell: Optional[Callable[[ShopItem, int], bool]] = None
        self.on_close: Optional[Callable[[], None]] = None

        # Build UI
        self._build_ui()

        # Focusable
        self.focusable = True

    def _build_ui(self) -> None:
        """Build shop UI."""
        self.clear_children()

        # Main panel
        self._main_panel = Panel()
        self._main_panel.set_title(f"SHOP - {self._shop_name}")
        self._main_panel.show_shadow = True
        self._main_panel.rect.width = 550
        self._main_panel.rect.height = 400
        self.add_child(self._main_panel)

        # Gold display
        self._gold_label = Label(f"Gold: {self._gold}")
        self._gold_label.set_position(self._main_panel.rect.width - 120, 8)
        self._main_panel.add_child(self._gold_label)

        # Mode menu
        self._menu_panel = Panel()
        self._menu_panel.show_border = True
        self._menu_panel.rect.width = 100
        self._menu_panel.rect.height = 100
        self._menu_panel.set_position(16, 50)
        self._main_panel.add_child(self._menu_panel)

        self._menu_layout = VBoxLayout()
        self._menu_layout.spacing = 4
        self._menu_layout.set_position(8, 8)
        self._menu_panel.add_child(self._menu_layout)

        buy_btn = Button("Buy")
        buy_btn.rect.width = 80
        buy_btn.set_on_click(lambda: self._set_mode("buy"))
        self._menu_layout.add_child(buy_btn)

        sell_btn = Button("Sell")
        sell_btn.rect.width = 80
        sell_btn.set_on_click(lambda: self._set_mode("sell"))
        self._menu_layout.add_child(sell_btn)

        leave_btn = Button("Leave")
        leave_btn.rect.width = 80
        leave_btn.set_on_click(self._on_leave)
        self._menu_layout.add_child(leave_btn)

        # Item list panel (hidden initially)
        self._list_panel = Panel()
        self._list_panel.rect.width = 280
        self._list_panel.rect.height = 220
        self._list_panel.set_position(16, 160)
        self._list_panel.visible = False
        self._main_panel.add_child(self._list_panel)

        self._item_list = SelectionList()
        self._item_list.rect.width = 260
        self._item_list.set_visible_count(7)
        self._item_list.set_position(8, 8)
        self._item_list.on_select = self._on_item_select
        self._item_list.on_selection_changed = self._on_selection_change
        self._list_panel.add_child(self._item_list)

        # Details panel
        self._details_panel = Panel()
        self._details_panel.rect.width = 220
        self._details_panel.rect.height = 220
        self._details_panel.set_position(310, 160)
        self._details_panel.visible = False
        self._main_panel.add_child(self._details_panel)

        self._details_layout = VBoxLayout()
        self._details_layout.spacing = 8
        self._details_layout.set_position(8, 8)
        self._details_panel.add_child(self._details_layout)

        self._detail_name = Label("")
        self._detail_name._font_size = 18
        self._details_layout.add_child(self._detail_name)

        self._detail_desc = Label("")
        self._detail_desc.max_width = 200
        self._details_layout.add_child(self._detail_desc)

        self._detail_price = Label("")
        self._details_layout.add_child(self._detail_price)

        self._detail_owned = Label("")
        self._details_layout.add_child(self._detail_owned)

        # Quantity and confirm
        self._qty_layout = HBoxLayout()
        self._qty_layout.spacing = 8

        self._qty_label = Label("Qty: 1")
        self._qty_layout.add_child(self._qty_label)

        self._confirm_btn = Button("Buy")
        self._confirm_btn.rect.width = 80
        self._confirm_btn.set_on_click(self._on_confirm_transaction)
        self._qty_layout.add_child(self._confirm_btn)

        self._details_layout.add_child(self._qty_layout)

    def set_gold(self, amount: int) -> 'ShopScreen':
        """Set player's gold."""
        self._gold = amount
        self._gold_label.text = f"Gold: {amount}"
        return self

    def set_buy_items(self, items: List[ShopItem]) -> 'ShopScreen':
        """Set items available to buy."""
        self._buy_items = items
        return self

    def set_sell_items(self, items: List[ShopItem]) -> 'ShopScreen':
        """Set items available to sell."""
        self._sell_items = items
        return self

    def _set_mode(self, mode: str) -> None:
        """Change shop mode."""
        self._mode = mode
        self._quantity = 1

        if mode == "buy":
            self._refresh_item_list(self._buy_items)
            self._confirm_btn.text = "Buy"
        elif mode == "sell":
            self._refresh_item_list(self._sell_items)
            self._confirm_btn.text = "Sell"

        self._list_panel.visible = mode in ("buy", "sell")
        self._details_panel.visible = mode in ("buy", "sell")

        if mode in ("buy", "sell"):
            self._item_list.focus()

    def _refresh_item_list(self, items: List[ShopItem]) -> None:
        """Refresh item list."""
        self._item_list.clear_items()

        for item in items:
            text = f"{item.name}  {item.price}G"
            can_afford = self._gold >= item.price if self._mode == "buy" else True
            self._item_list.add_item(text, value=item, enabled=can_afford)

        if items:
            self._selected_item = items[0]
            self._update_details()

    def _on_selection_change(self, index: int) -> None:
        """Handle selection cursor move."""
        items = self._buy_items if self._mode == "buy" else self._sell_items
        if 0 <= index < len(items):
            self._selected_item = items[index]
            self._quantity = 1
            self._update_details()

    def _update_details(self) -> None:
        """Update details panel."""
        if self._selected_item:
            self._detail_name.text = self._selected_item.name
            self._detail_desc.text = self._selected_item.description
            self._detail_price.text = f"Price: {self._selected_item.price}G"
            self._detail_owned.text = f"Owned: {self._selected_item.owned}"
            self._qty_label.text = f"Qty: {self._quantity}"

    def _on_item_select(self, index: int, item: ListItem) -> None:
        """Handle item confirm (buy/sell)."""
        self._on_confirm_transaction()

    def _on_confirm_transaction(self) -> None:
        """Execute buy/sell transaction."""
        if not self._selected_item:
            return

        if self._mode == "buy":
            if self.on_buy:
                success = self.on_buy(self._selected_item, self._quantity)
                if success:
                    self._gold -= self._selected_item.price * self._quantity
                    self._gold_label.text = f"Gold: {self._gold}"
        elif self._mode == "sell":
            if self.on_sell:
                success = self.on_sell(self._selected_item, self._quantity)
                if success:
                    self._gold += self._selected_item.price * self._quantity
                    self._gold_label.text = f"Gold: {self._gold}"

    def _on_leave(self) -> None:
        """Leave the shop."""
        if self.on_close:
            self.on_close()
        if self.manager:
            self.manager.pop_modal()

    # Input

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """Navigate shop UI."""
        if self._mode in ("buy", "sell"):
            # Left/right changes quantity
            if col_delta != 0:
                self._quantity = max(1, min(99, self._quantity + col_delta))
                self._qty_label.text = f"Qty: {self._quantity}"
                return True
            return self._item_list.navigate(row_delta, col_delta)

        return self._menu_layout.navigate(row_delta, col_delta)

    def on_confirm(self) -> bool:
        """Confirm selection."""
        if self._mode in ("buy", "sell"):
            return self._item_list.on_confirm()
        return self._menu_layout.on_confirm()

    def on_cancel(self) -> bool:
        """Cancel/back."""
        if self._mode in ("buy", "sell"):
            self._mode = "menu"
            self._list_panel.visible = False
            self._details_panel.visible = False
            self._menu_layout.focus_first()
            return True

        self._on_leave()
        return True

    def focus(self) -> bool:
        """Focus menu."""
        if super().focus():
            self._menu_layout.focus_first()
            return True
        return False

    def layout(self) -> None:
        """Center panel."""
        if self._main_panel:
            self._main_panel.rect.x = (self.rect.width - self._main_panel.rect.width) / 2
            self._main_panel.rect.y = (self.rect.height - self._main_panel.rect.height) / 2
        super().layout()

    def render(self, renderer: 'UIRenderer') -> None:
        """Render shop screen."""
        x, y = self.absolute_position
        renderer.draw_rect(x, y, self.rect.width, self.rect.height, (0, 0, 0, 180))
        super().render(renderer)
