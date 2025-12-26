"""
Equipment screen preset - Equipment management UI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable, List, Dict, Any
from dataclasses import dataclass

from engine.ui.container import Container
from engine.ui.widgets.label import Label
from engine.ui.widgets.panel import Panel
from engine.ui.widgets.button import Button
from engine.ui.widgets.selection_list import SelectionList, ListItem
from engine.ui.widgets.image import Image
from engine.ui.layouts.horizontal import HBoxLayout
from engine.ui.layouts.vertical import VBoxLayout
from engine.ui.widget import Padding

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


@dataclass
class EquipmentSlot:
    """Equipment slot definition."""
    id: str
    name: str
    equipped_item: Optional[Any] = None
    icon: Optional[str] = None


@dataclass
class EquipmentItem:
    """Equipment item data."""
    id: str
    name: str
    slot_type: str  # "weapon", "armor", "accessory", etc.
    icon: Optional[str] = None
    stats: Dict[str, int] = None
    description: str = ""


class EquipmentScreen(Container):
    """
    Equipment management screen.

    Layout:
    ┌─────────────────────────────────────────┐
    │ EQUIPMENT - [Character Name]            │
    ├───────────────┬─────────────────────────┤
    │               │                         │
    │  [Portrait]   │  Weapon: [Item]    ▶    │
    │               │  Shield: [Item]    ▶    │
    │  Stats:       │  Helmet: [Item]    ▶    │
    │  ATK: 50      │  Armor:  [Item]    ▶    │
    │  DEF: 30      │  Acc 1:  [Item]    ▶    │
    │  ...          │  Acc 2:  [Item]    ▶    │
    │               │                         │
    └───────────────┴─────────────────────────┘
    """

    def __init__(self):
        super().__init__()

        self._character_name = "Character"
        self._portrait: Optional[str] = None
        self._stats: Dict[str, int] = {}
        self._slots: List[EquipmentSlot] = []
        self._available_items: List[EquipmentItem] = []

        # Currently selected
        self._selected_slot_index = 0
        self._showing_items = False

        # Callbacks
        self.on_equip: Optional[Callable[[str, EquipmentItem], None]] = None
        self.on_unequip: Optional[Callable[[str], None]] = None
        self.on_close: Optional[Callable[[], None]] = None

        # Build UI
        self._build_ui()

        # Focusable
        self.focusable = True

    def _build_ui(self) -> None:
        """Build equipment UI."""
        self.clear_children()

        # Main panel
        self._main_panel = Panel()
        self._main_panel.set_title(f"EQUIPMENT - {self._character_name}")
        self._main_panel.show_shadow = True
        self._main_panel.rect.width = 500
        self._main_panel.rect.height = 350
        self.add_child(self._main_panel)

        # Content layout
        self._content = HBoxLayout()
        self._content.spacing = 16
        self._content.padding = Padding(top=40, right=16, bottom=16, left=16)
        self._main_panel.add_child(self._content)

        # Left panel: Portrait and stats
        self._left_panel = VBoxLayout()
        self._left_panel.spacing = 8
        self._left_panel.rect.width = 150
        self._content.add_child(self._left_panel)

        # Portrait
        if self._portrait:
            self._portrait_img = Image(self._portrait)
            self._portrait_img.rect.width = 128
            self._portrait_img.rect.height = 128
            self._left_panel.add_child(self._portrait_img)

        # Stats
        self._stats_label = Label("Stats:")
        self._stats_label._font_size = 14
        self._left_panel.add_child(self._stats_label)

        self._stats_content = Label("")
        self._left_panel.add_child(self._stats_content)
        self._update_stats_display()

        # Right panel: Equipment slots
        self._right_panel = VBoxLayout()
        self._right_panel.spacing = 4
        self._content.add_child(self._right_panel)

        # Slot list
        self._slot_list = SelectionList()
        self._slot_list.rect.width = 280
        self._slot_list.set_visible_count(8)
        self._slot_list.on_select = self._on_slot_selected
        self._right_panel.add_child(self._slot_list)

        # Item selection list (hidden initially)
        self._item_list = SelectionList()
        self._item_list.rect.width = 280
        self._item_list.set_visible_count(6)
        self._item_list.visible = False
        self._item_list.on_select = self._on_item_selected
        self._right_panel.add_child(self._item_list)

        self._refresh_slots()

    def set_character(
        self,
        name: str,
        portrait: Optional[str] = None,
        stats: Optional[Dict[str, int]] = None,
    ) -> 'EquipmentScreen':
        """Set character info."""
        self._character_name = name
        self._portrait = portrait
        self._stats = stats or {}
        self._build_ui()
        return self

    def set_slots(self, slots: List[EquipmentSlot]) -> 'EquipmentScreen':
        """Set equipment slots."""
        self._slots = slots
        self._refresh_slots()
        return self

    def set_available_items(self, items: List[EquipmentItem]) -> 'EquipmentScreen':
        """Set available items for equipping."""
        self._available_items = items
        return self

    def _refresh_slots(self) -> None:
        """Refresh slot list display."""
        self._slot_list.clear_items()
        for slot in self._slots:
            equipped = slot.equipped_item.name if slot.equipped_item else "(Empty)"
            self._slot_list.add_item(f"{slot.name}: {equipped}", value=slot)

    def _update_stats_display(self) -> None:
        """Update stats display."""
        lines = []
        for stat, value in self._stats.items():
            lines.append(f"{stat}: {value}")
        self._stats_content.text = "\n".join(lines)

    def _on_slot_selected(self, index: int, item: ListItem) -> None:
        """Handle slot selection."""
        self._selected_slot_index = index
        slot = self._slots[index]

        # Show available items for this slot
        self._show_item_list(slot)

    def _show_item_list(self, slot: EquipmentSlot) -> None:
        """Show items available for the slot."""
        self._item_list.clear_items()

        # Add unequip option if something equipped
        if slot.equipped_item:
            self._item_list.add_item("(Unequip)", value=None)

        # Add matching items
        for item in self._available_items:
            if item.slot_type == slot.id:
                self._item_list.add_item(item.name, value=item, icon=item.icon)

        self._item_list.visible = True
        self._slot_list.visible = False
        self._showing_items = True
        self._item_list.focus()

    def _on_item_selected(self, index: int, item: ListItem) -> None:
        """Handle item selection."""
        slot = self._slots[self._selected_slot_index]

        if item.value is None:
            # Unequip
            if self.on_unequip:
                self.on_unequip(slot.id)
        else:
            # Equip item
            if self.on_equip:
                self.on_equip(slot.id, item.value)

        # Return to slot view
        self._hide_item_list()

    def _hide_item_list(self) -> None:
        """Hide item list and return to slots."""
        self._item_list.visible = False
        self._slot_list.visible = True
        self._showing_items = False
        self._slot_list.focus()
        self._refresh_slots()

    # Input

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """Navigate lists."""
        if self._showing_items:
            return self._item_list.navigate(row_delta, col_delta)
        return self._slot_list.navigate(row_delta, col_delta)

    def on_confirm(self) -> bool:
        """Confirm selection."""
        if self._showing_items:
            return self._item_list.on_confirm()
        return self._slot_list.on_confirm()

    def on_cancel(self) -> bool:
        """Cancel - back to slots or close."""
        if self._showing_items:
            self._hide_item_list()
            return True

        if self.on_close:
            self.on_close()
        if self.manager:
            self.manager.pop_modal()
        return True

    def focus(self) -> bool:
        """Focus slot list."""
        if super().focus():
            self._slot_list.focus()
            return True
        return False

    def layout(self) -> None:
        """Center panel."""
        if self._main_panel:
            self._main_panel.rect.x = (self.rect.width - self._main_panel.rect.width) / 2
            self._main_panel.rect.y = (self.rect.height - self._main_panel.rect.height) / 2
        super().layout()

    def render(self, renderer: 'UIRenderer') -> None:
        """Render equipment screen."""
        x, y = self.absolute_position
        renderer.draw_rect(x, y, self.rect.width, self.rect.height, (0, 0, 0, 180))
        super().render(renderer)
