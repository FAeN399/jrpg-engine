"""
Status screen preset - Character status display.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable, List, Dict, Any
from dataclasses import dataclass

from engine.ui.container import Container
from engine.ui.widgets.label import Label
from engine.ui.widgets.panel import Panel
from engine.ui.widgets.progress_bar import ProgressBar
from engine.ui.widgets.image import Image
from engine.ui.layouts.horizontal import HBoxLayout
from engine.ui.layouts.vertical import VBoxLayout
from engine.ui.widget import Padding

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


@dataclass
class CharacterStatus:
    """Character status data."""
    name: str
    level: int = 1
    exp: int = 0
    exp_to_next: int = 100
    hp: int = 100
    max_hp: int = 100
    mp: int = 50
    max_mp: int = 50
    portrait: Optional[str] = None
    stats: Dict[str, int] = None
    status_effects: List[str] = None


class StatusScreen(Container):
    """
    Character status display screen.

    Layout:
    ┌─────────────────────────────────────────┐
    │ STATUS                            1/4   │
    ├───────────────┬─────────────────────────┤
    │               │  [Name]     Lv. XX      │
    │  [Portrait]   │  Class: Fighter         │
    │               │                         │
    │               │  HP: ████████░░ 100/100 │
    │               │  MP: ████░░░░░░  30/50  │
    │               │  EXP: ██████░░░  60%    │
    ├───────────────┴─────────────────────────┤
    │  ATK: 50    DEF: 30    SPD: 20          │
    │  MAG: 25    RES: 20    LUK: 15          │
    ├─────────────────────────────────────────┤
    │  Status: Poisoned, Weakened             │
    └─────────────────────────────────────────┘
    """

    def __init__(self):
        super().__init__()

        self._characters: List[CharacterStatus] = []
        self._current_index = 0

        # Callbacks
        self.on_close: Optional[Callable[[], None]] = None

        # Build UI
        self._build_ui()

        # Focusable
        self.focusable = True

    def _build_ui(self) -> None:
        """Build status UI."""
        self.clear_children()

        # Main panel
        self._main_panel = Panel()
        self._main_panel.set_title("STATUS")
        self._main_panel.show_shadow = True
        self._main_panel.rect.width = 500
        self._main_panel.rect.height = 400
        self._main_panel.padding = Padding.all(8)
        self.add_child(self._main_panel)

        # Page indicator (top right)
        self._page_label = Label("")
        self._page_label.set_position(self._main_panel.rect.width - 60, 8)
        self._main_panel.add_child(self._page_label)

        # Content layout
        self._content = VBoxLayout()
        self._content.spacing = 16
        self._content.set_position(8, 40)
        self._main_panel.add_child(self._content)

        # Top section (portrait + basic info)
        self._top_section = HBoxLayout()
        self._top_section.spacing = 16
        self._content.add_child(self._top_section)

        # Portrait
        self._portrait = Image()
        self._portrait.rect.width = 128
        self._portrait.rect.height = 128
        self._top_section.add_child(self._portrait)

        # Basic info
        self._info_section = VBoxLayout()
        self._info_section.spacing = 8
        self._top_section.add_child(self._info_section)

        self._name_label = Label("")
        self._name_label._font_size = 24
        self._info_section.add_child(self._name_label)

        self._level_label = Label("")
        self._info_section.add_child(self._level_label)

        # HP bar
        self._hp_layout = HBoxLayout()
        self._hp_layout.spacing = 8
        hp_label = Label("HP:")
        hp_label.rect.width = 30
        self._hp_layout.add_child(hp_label)
        self._hp_bar = ProgressBar.hp_bar(100, 100)
        self._hp_bar.rect.width = 200
        self._hp_layout.add_child(self._hp_bar)
        self._info_section.add_child(self._hp_layout)

        # MP bar
        self._mp_layout = HBoxLayout()
        self._mp_layout.spacing = 8
        mp_label = Label("MP:")
        mp_label.rect.width = 30
        self._mp_layout.add_child(mp_label)
        self._mp_bar = ProgressBar.mp_bar(50, 50)
        self._mp_bar.rect.width = 200
        self._mp_layout.add_child(self._mp_bar)
        self._info_section.add_child(self._mp_layout)

        # EXP bar
        self._exp_layout = HBoxLayout()
        self._exp_layout.spacing = 8
        exp_label = Label("EXP:")
        exp_label.rect.width = 30
        self._exp_layout.add_child(exp_label)
        self._exp_bar = ProgressBar.exp_bar(0, 100)
        self._exp_bar.rect.width = 200
        self._exp_layout.add_child(self._exp_bar)
        self._info_section.add_child(self._exp_layout)

        # Stats section
        self._stats_panel = Panel()
        self._stats_panel.set_title("Stats")
        self._stats_panel.rect.width = 460
        self._stats_panel.rect.height = 80
        self._content.add_child(self._stats_panel)

        self._stats_label = Label("")
        self._stats_label.set_position(16, 30)
        self._stats_panel.add_child(self._stats_label)

        # Status effects section
        self._effects_panel = Panel()
        self._effects_panel.set_title("Status Effects")
        self._effects_panel.rect.width = 460
        self._effects_panel.rect.height = 50
        self._content.add_child(self._effects_panel)

        self._effects_label = Label("None")
        self._effects_label.set_position(16, 30)
        self._effects_panel.add_child(self._effects_label)

    def set_characters(self, characters: List[CharacterStatus]) -> 'StatusScreen':
        """Set character list."""
        self._characters = characters
        self._current_index = 0
        self._refresh_display()
        return self

    def _refresh_display(self) -> None:
        """Refresh display for current character."""
        if not self._characters:
            return

        char = self._characters[self._current_index]

        # Page indicator
        self._page_label.text = f"{self._current_index + 1}/{len(self._characters)}"

        # Basic info
        self._name_label.text = char.name
        self._level_label.text = f"Level {char.level}"

        # Portrait
        if char.portrait:
            self._portrait.path = char.portrait

        # Bars
        self._hp_bar.set_value(char.hp, char.max_hp)
        self._mp_bar.set_value(char.mp, char.max_mp)
        self._exp_bar.set_value(char.exp, char.exp_to_next)

        # Stats
        if char.stats:
            stat_lines = []
            stats_per_line = 3
            stat_items = list(char.stats.items())

            for i in range(0, len(stat_items), stats_per_line):
                line_stats = stat_items[i:i+stats_per_line]
                line = "    ".join(f"{k}: {v}" for k, v in line_stats)
                stat_lines.append(line)

            self._stats_label.text = "\n".join(stat_lines)

        # Status effects
        if char.status_effects:
            self._effects_label.text = ", ".join(char.status_effects)
        else:
            self._effects_label.text = "None"

    def next_character(self) -> None:
        """Show next character."""
        if self._characters:
            self._current_index = (self._current_index + 1) % len(self._characters)
            self._refresh_display()

    def prev_character(self) -> None:
        """Show previous character."""
        if self._characters:
            self._current_index = (self._current_index - 1) % len(self._characters)
            self._refresh_display()

    # Input

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """Navigate between characters."""
        if col_delta > 0:
            self.next_character()
            return True
        elif col_delta < 0:
            self.prev_character()
            return True
        return False

    def on_confirm(self) -> bool:
        """Confirm does nothing."""
        return False

    def on_cancel(self) -> bool:
        """Close status screen."""
        if self.on_close:
            self.on_close()
        if self.manager:
            self.manager.pop_modal()
        return True

    def layout(self) -> None:
        """Center panel."""
        if self._main_panel:
            self._main_panel.rect.x = (self.rect.width - self._main_panel.rect.width) / 2
            self._main_panel.rect.y = (self.rect.height - self._main_panel.rect.height) / 2
        super().layout()

    def render(self, renderer: 'UIRenderer') -> None:
        """Render status screen."""
        x, y = self.absolute_position
        renderer.draw_rect(x, y, self.rect.width, self.rect.height, (0, 0, 0, 180))
        super().render(renderer)
