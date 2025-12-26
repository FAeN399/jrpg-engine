"""
Battle HUD preset - In-battle UI overlay.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable, List, Dict
from dataclasses import dataclass

from engine.ui.container import Container
from engine.ui.widgets.label import Label
from engine.ui.widgets.panel import Panel
from engine.ui.widgets.progress_bar import ProgressBar
from engine.ui.widgets.selection_list import SelectionList, ListItem
from engine.ui.layouts.vertical import VBoxLayout
from engine.ui.layouts.horizontal import HBoxLayout
from engine.ui.layouts.anchor import AnchorLayout, Anchor
from engine.ui.widget import Padding

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


@dataclass
class BattleActor:
    """Battle actor data for HUD display."""
    name: str
    hp: int
    max_hp: int
    mp: int = 0
    max_mp: int = 0
    is_player: bool = True
    is_active: bool = False
    status_icons: List[str] = None


@dataclass
class BattleCommand:
    """Battle command option."""
    id: str
    name: str
    enabled: bool = True
    mp_cost: int = 0


class BattleHUD(Container):
    """
    Battle UI overlay.

    Layout:
    ┌─────────────────────────────────────────┐
    │                                         │
    │                 [BATTLE AREA]           │
    │                                         │
    ├─────────────────────────────────────────┤
    │  ┌─────────┐  ┌────────────────────┐    │
    │  │ COMMAND │  │ Party Status       │    │
    │  │ Attack  │  │ Hero   HP ████░░░  │    │
    │  │ Magic   │  │ Mage   HP ███░░░░  │    │
    │  │ Item    │  │ Knight HP █████░░  │    │
    │  │ Defend  │  └────────────────────┘    │
    │  │ Run     │                            │
    │  └─────────┘                            │
    └─────────────────────────────────────────┘
    """

    def __init__(self):
        super().__init__()

        self._party: List[BattleActor] = []
        self._enemies: List[BattleActor] = []
        self._commands: List[BattleCommand] = []

        # State
        self._command_visible = False
        self._target_mode = False

        # Callbacks
        self.on_command_select: Optional[Callable[[str], None]] = None
        self.on_target_select: Optional[Callable[[int, bool], None]] = None  # index, is_enemy

        # Build UI
        self._build_ui()

        # Focusable
        self.focusable = True

    def _build_ui(self) -> None:
        """Build battle HUD."""
        self.clear_children()

        # Use anchor layout for positioning
        self._anchor = AnchorLayout()
        self.add_child(self._anchor)

        # Party status (bottom right)
        self._party_panel = Panel()
        self._party_panel.set_title("Party")
        self._party_panel.rect.width = 280
        self._party_panel.rect.height = 120
        self._anchor.add_child(self._party_panel)
        self._anchor.set_anchor(
            self._party_panel,
            Anchor.BOTTOM_RIGHT,
            margin_right=16,
            margin_bottom=16
        )

        self._party_layout = VBoxLayout()
        self._party_layout.spacing = 4
        self._party_layout.set_position(8, 28)
        self._party_panel.add_child(self._party_layout)

        # Command menu (bottom left)
        self._command_panel = Panel()
        self._command_panel.set_title("Command")
        self._command_panel.rect.width = 140
        self._command_panel.rect.height = 160
        self._command_panel.visible = False
        self._anchor.add_child(self._command_panel)
        self._anchor.set_anchor(
            self._command_panel,
            Anchor.BOTTOM_LEFT,
            margin_left=16,
            margin_bottom=16
        )

        self._command_list = SelectionList()
        self._command_list.rect.width = 120
        self._command_list.set_visible_count(5)
        self._command_list.set_position(8, 28)
        self._command_list.on_select = self._on_command_selected
        self._command_panel.add_child(self._command_list)

        # Message display (top)
        self._message_panel = Panel()
        self._message_panel.show_border = True
        self._message_panel.rect.width = 400
        self._message_panel.rect.height = 50
        self._message_panel.visible = False
        self._anchor.add_child(self._message_panel)
        self._anchor.set_anchor(
            self._message_panel,
            Anchor.TOP_CENTER,
            margin_top=16
        )

        self._message_label = Label("")
        self._message_label.align = "center"
        self._message_label.set_position(200, 15)
        self._message_panel.add_child(self._message_label)

        # Target indicator (for targeting)
        self._target_label = Label("")
        self._target_label.visible = False
        self._target_label._color = (255, 255, 100)
        self._anchor.add_child(self._target_label)

    def set_party(self, party: List[BattleActor]) -> 'BattleHUD':
        """Set party members."""
        self._party = party
        self._refresh_party_display()
        return self

    def set_enemies(self, enemies: List[BattleActor]) -> 'BattleHUD':
        """Set enemy actors."""
        self._enemies = enemies
        return self

    def set_commands(self, commands: List[BattleCommand]) -> 'BattleHUD':
        """Set available commands."""
        self._commands = commands
        self._refresh_command_list()
        return self

    def _refresh_party_display(self) -> None:
        """Refresh party status display."""
        self._party_layout.clear_children()

        for actor in self._party:
            # Actor row
            row = HBoxLayout()
            row.spacing = 8

            # Name
            name = Label(actor.name)
            name.rect.width = 60
            if actor.is_active:
                name._color = (255, 255, 100)
            row.add_child(name)

            # HP bar
            hp_bar = ProgressBar.hp_bar(actor.hp, actor.max_hp)
            hp_bar.rect.width = 100
            hp_bar.rect.height = 14
            row.add_child(hp_bar)

            # MP (if has MP)
            if actor.max_mp > 0:
                mp_label = Label(f"{actor.mp}")
                mp_label._font_size = 12
                mp_label.rect.width = 40
                row.add_child(mp_label)

            self._party_layout.add_child(row)

        self._party_layout.layout()

    def _refresh_command_list(self) -> None:
        """Refresh command list."""
        self._command_list.clear_items()

        for cmd in self._commands:
            text = cmd.name
            if cmd.mp_cost > 0:
                text += f" ({cmd.mp_cost})"
            self._command_list.add_item(text, value=cmd, enabled=cmd.enabled)

    def show_commands(self, show: bool = True) -> None:
        """Show/hide command menu."""
        self._command_panel.visible = show
        self._command_visible = show

        if show:
            self._command_list.focus()

    def show_message(self, text: str) -> None:
        """Show battle message."""
        self._message_label.text = text
        self._message_panel.visible = True

    def hide_message(self) -> None:
        """Hide battle message."""
        self._message_panel.visible = False

    def set_active_actor(self, index: int) -> None:
        """Set the active actor (highlight in status)."""
        for i, actor in enumerate(self._party):
            actor.is_active = (i == index)
        self._refresh_party_display()

    def _on_command_selected(self, index: int, item: ListItem) -> None:
        """Handle command selection."""
        if item.value and self.on_command_select:
            self.on_command_select(item.value.id)

    # Input

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """Navigate command list."""
        if self._command_visible:
            return self._command_list.navigate(row_delta, col_delta)
        return False

    def on_confirm(self) -> bool:
        """Confirm command."""
        if self._command_visible:
            return self._command_list.on_confirm()
        return False

    def on_cancel(self) -> bool:
        """Cancel (go back)."""
        if self._command_visible:
            self.show_commands(False)
            return True
        return False

    def focus(self) -> bool:
        """Focus command list."""
        if super().focus():
            if self._command_visible:
                self._command_list.focus()
            return True
        return False

    def layout(self) -> None:
        """Layout HUD elements."""
        self._anchor.rect.width = self.rect.width
        self._anchor.rect.height = self.rect.height
        self._anchor.layout()

    def render(self, renderer: 'UIRenderer') -> None:
        """Render battle HUD (no background - overlay only)."""
        super().render(renderer)
