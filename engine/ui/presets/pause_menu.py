"""
Pause menu preset - In-game pause screen.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable, List

from engine.ui.container import Container
from engine.ui.widgets.label import Label
from engine.ui.widgets.button import Button
from engine.ui.widgets.panel import Panel
from engine.ui.layouts.vertical import VBoxLayout
from engine.ui.widget import Padding

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


class PauseMenu(Container):
    """
    In-game pause menu.

    Features:
    - Resume game
    - Inventory/Status access
    - Save/Load game
    - Options
    - Return to title
    - Semi-transparent overlay
    """

    def __init__(self):
        super().__init__()

        # Callbacks
        self.on_resume: Optional[Callable[[], None]] = None
        self.on_inventory: Optional[Callable[[], None]] = None
        self.on_status: Optional[Callable[[], None]] = None
        self.on_save: Optional[Callable[[], None]] = None
        self.on_load: Optional[Callable[[], None]] = None
        self.on_options: Optional[Callable[[], None]] = None
        self.on_quit_to_title: Optional[Callable[[], None]] = None

        # Menu options to show
        self._show_inventory = True
        self._show_status = True
        self._show_save = True
        self._show_load = True
        self._show_options = True

        # Build UI
        self._build_ui()

        # Focusable
        self.focusable = True

    def _build_ui(self) -> None:
        """Build the pause menu UI."""
        self.clear_children()

        # Menu panel
        self._panel = Panel()
        self._panel.set_title("PAUSED")
        self._panel.show_shadow = True

        # Button layout inside panel
        self._button_layout = VBoxLayout()
        self._button_layout.spacing = 8
        self._button_layout.padding = Padding(top=40, right=16, bottom=16, left=16)
        self._panel.add_child(self._button_layout)

        # Create buttons
        button_width = 160

        # Resume
        resume_btn = Button("Resume")
        resume_btn.rect.width = button_width
        resume_btn.set_on_click(self._on_resume)
        self._button_layout.add_child(resume_btn)

        # Inventory
        if self._show_inventory:
            inv_btn = Button("Inventory")
            inv_btn.rect.width = button_width
            inv_btn.set_on_click(self._on_inventory)
            self._button_layout.add_child(inv_btn)

        # Status
        if self._show_status:
            status_btn = Button("Status")
            status_btn.rect.width = button_width
            status_btn.set_on_click(self._on_status)
            self._button_layout.add_child(status_btn)

        # Save
        if self._show_save:
            save_btn = Button("Save Game")
            save_btn.rect.width = button_width
            save_btn.set_on_click(self._on_save)
            self._button_layout.add_child(save_btn)

        # Load
        if self._show_load:
            load_btn = Button("Load Game")
            load_btn.rect.width = button_width
            load_btn.set_on_click(self._on_load)
            self._button_layout.add_child(load_btn)

        # Options
        if self._show_options:
            options_btn = Button("Options")
            options_btn.rect.width = button_width
            options_btn.set_on_click(self._on_options)
            self._button_layout.add_child(options_btn)

        # Quit to Title
        quit_btn = Button("Quit to Title")
        quit_btn.rect.width = button_width
        quit_btn.set_on_click(self._on_quit)
        self._button_layout.add_child(quit_btn)

        # Calculate panel size
        self._button_layout.fit_content = True
        self._button_layout.layout()

        pref_w, pref_h = self._button_layout.get_preferred_size()
        self._panel.rect.width = pref_w
        self._panel.rect.height = pref_h

        self.add_child(self._panel)

    def set_show_inventory(self, show: bool) -> 'PauseMenu':
        self._show_inventory = show
        self._build_ui()
        return self

    def set_show_status(self, show: bool) -> 'PauseMenu':
        self._show_status = show
        self._build_ui()
        return self

    def set_show_save(self, show: bool) -> 'PauseMenu':
        self._show_save = show
        self._build_ui()
        return self

    def set_show_load(self, show: bool) -> 'PauseMenu':
        self._show_load = show
        self._build_ui()
        return self

    def _on_resume(self) -> None:
        if self.on_resume:
            self.on_resume()
        if self.manager:
            self.manager.pop_modal()

    def _on_inventory(self) -> None:
        if self.on_inventory:
            self.on_inventory()

    def _on_status(self) -> None:
        if self.on_status:
            self.on_status()

    def _on_save(self) -> None:
        if self.on_save:
            self.on_save()

    def _on_load(self) -> None:
        if self.on_load:
            self.on_load()

    def _on_options(self) -> None:
        if self.on_options:
            self.on_options()

    def _on_quit(self) -> None:
        if self.on_quit_to_title:
            self.on_quit_to_title()

    # Input

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """Navigate menu."""
        if self._button_layout:
            return self._button_layout.navigate(row_delta, col_delta)
        return False

    def on_confirm(self) -> bool:
        """Confirm selection."""
        if self._button_layout:
            return self._button_layout.on_confirm()
        return False

    def on_cancel(self) -> bool:
        """Cancel = Resume."""
        self._on_resume()
        return True

    def focus(self) -> bool:
        """Focus first button."""
        if super().focus():
            if self._button_layout:
                self._button_layout.focus_first()
            return True
        return False

    def layout(self) -> None:
        """Center panel in container."""
        if self._panel:
            self._panel.rect.x = (self.rect.width - self._panel.rect.width) / 2
            self._panel.rect.y = (self.rect.height - self._panel.rect.height) / 2
        super().layout()

    # Rendering

    def render(self, renderer: 'UIRenderer') -> None:
        """Render pause menu with dimmed background."""
        x, y = self.absolute_position

        # Dim overlay
        renderer.draw_rect(
            x, y, self.rect.width, self.rect.height,
            (0, 0, 0, 150)
        )

        # Render children (panel)
        super().render(renderer)
