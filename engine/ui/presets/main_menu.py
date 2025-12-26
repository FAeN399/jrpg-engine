"""
Main menu preset - Title screen menu.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable, List, Tuple

from engine.ui.container import Container
from engine.ui.widgets.label import Label
from engine.ui.widgets.button import Button
from engine.ui.widgets.image import Image
from engine.ui.layouts.vertical import VBoxLayout
from engine.ui.layouts.anchor import AnchorLayout, Anchor
from engine.ui.widget import Padding

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


class MainMenu(Container):
    """
    Title screen main menu.

    Features:
    - Game title display
    - Menu options (New Game, Continue, Options, Quit)
    - Background image support
    - Logo/artwork display
    - Version number
    """

    def __init__(
        self,
        title: str = "JRPG Game",
        show_continue: bool = False,
    ):
        super().__init__()

        self._title = title
        self._show_continue = show_continue
        self._version = ""

        # Callbacks for menu options
        self.on_new_game: Optional[Callable[[], None]] = None
        self.on_continue: Optional[Callable[[], None]] = None
        self.on_options: Optional[Callable[[], None]] = None
        self.on_quit: Optional[Callable[[], None]] = None

        # Visual options
        self._background: Optional[str] = None
        self._logo: Optional[str] = None

        # Menu buttons
        self._buttons: List[Button] = []

        # Build UI
        self._build_ui()

        # Focusable
        self.focusable = True

    def _build_ui(self) -> None:
        """Build the main menu UI."""
        self.clear_children()

        # Use anchor layout for positioning
        self._anchor = AnchorLayout()
        self._anchor.rect.width = self.rect.width
        self._anchor.rect.height = self.rect.height
        self.add_child(self._anchor)

        # Title label (top center)
        self._title_label = Label(self._title)
        self._title_label._font_size = 48
        self._title_label.align = "center"
        self._anchor.add_child(self._title_label)
        self._anchor.set_anchor(self._title_label, Anchor.TOP_CENTER, margin_top=80)

        # Menu buttons (center)
        self._button_layout = VBoxLayout()
        self._button_layout.spacing = 12
        self._button_layout.align_items = "center"
        self._anchor.add_child(self._button_layout)
        self._anchor.set_anchor(self._button_layout, Anchor.CENTER, margin_top=50)

        # Create buttons
        self._buttons.clear()

        # New Game
        new_game_btn = Button("New Game")
        new_game_btn.rect.width = 180
        new_game_btn.set_on_click(self._on_new_game)
        self._buttons.append(new_game_btn)
        self._button_layout.add_child(new_game_btn)

        # Continue (if save exists)
        if self._show_continue:
            continue_btn = Button("Continue")
            continue_btn.rect.width = 180
            continue_btn.set_on_click(self._on_continue)
            self._buttons.append(continue_btn)
            self._button_layout.add_child(continue_btn)

        # Options
        options_btn = Button("Options")
        options_btn.rect.width = 180
        options_btn.set_on_click(self._on_options)
        self._buttons.append(options_btn)
        self._button_layout.add_child(options_btn)

        # Quit
        quit_btn = Button("Quit")
        quit_btn.rect.width = 180
        quit_btn.set_on_click(self._on_quit)
        self._buttons.append(quit_btn)
        self._button_layout.add_child(quit_btn)

        # Version label (bottom right)
        if self._version:
            version_label = Label(self._version)
            version_label._font_size = 12
            self._anchor.add_child(version_label)
            self._anchor.set_anchor(version_label, Anchor.BOTTOM_RIGHT, margin_right=10, margin_bottom=10)

        self._button_layout.layout()

    def set_title(self, title: str) -> 'MainMenu':
        """Set game title."""
        self._title = title
        self._title_label.text = title
        return self

    def set_version(self, version: str) -> 'MainMenu':
        """Set version string."""
        self._version = version
        self._build_ui()
        return self

    def set_show_continue(self, show: bool) -> 'MainMenu':
        """Show/hide continue option."""
        self._show_continue = show
        self._build_ui()
        return self

    def set_background(self, path: str) -> 'MainMenu':
        """Set background image."""
        self._background = path
        return self

    def _on_new_game(self) -> None:
        if self.on_new_game:
            self.on_new_game()

    def _on_continue(self) -> None:
        if self.on_continue:
            self.on_continue()

    def _on_options(self) -> None:
        if self.on_options:
            self.on_options()

    def _on_quit(self) -> None:
        if self.on_quit:
            self.on_quit()

    # Input

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """Navigate menu options."""
        if self._button_layout:
            return self._button_layout.navigate(row_delta, col_delta)
        return False

    def on_confirm(self) -> bool:
        """Confirm selection."""
        if self._button_layout:
            return self._button_layout.on_confirm()
        return False

    def on_cancel(self) -> bool:
        """Cancel does nothing on main menu."""
        return False

    def focus(self) -> bool:
        """Focus first button."""
        if super().focus():
            if self._button_layout:
                self._button_layout.focus_first()
            return True
        return False

    # Rendering

    def render(self, renderer: 'UIRenderer') -> None:
        """Render the main menu."""
        x, y = self.absolute_position
        theme = self.theme

        # Background
        if self._background:
            renderer.draw_sprite(self._background, x, y, self.rect.width, self.rect.height)
        else:
            # Gradient or solid background
            renderer.draw_rect(
                x, y, self.rect.width, self.rect.height,
                theme.colors.bg_primary
            )

        # Render children
        super().render(renderer)
