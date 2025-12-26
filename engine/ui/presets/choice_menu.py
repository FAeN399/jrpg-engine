"""
Choice menu preset - Yes/No and multiple choice selection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable, List

from engine.ui.container import Container
from engine.ui.widgets.label import Label
from engine.ui.widgets.button import Button
from engine.ui.layouts.vertical import VBoxLayout
from engine.ui.widget import Padding

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


class ChoiceMenu(Container):
    """
    Choice selection menu.

    Features:
    - Prompt text
    - Multiple choice options
    - Keyboard/gamepad navigation
    - Selection callback
    - Cancel option
    """

    def __init__(
        self,
        prompt: str = "",
        choices: Optional[List[str]] = None,
    ):
        super().__init__()

        self._prompt = prompt
        self._choices = choices or []
        self._selected_index = 0
        self._allow_cancel = True

        # Callbacks
        self.on_select: Optional[Callable[[int, str], None]] = None
        self.on_cancel: Optional[Callable[[], None]] = None

        # Build UI
        self._build_ui()

        # Focusable
        self.focusable = True

    def _build_ui(self) -> None:
        """Build the choice menu UI."""
        self.clear_children()

        # Main layout
        self._layout = VBoxLayout()
        self._layout.spacing = 8
        self._layout.padding = Padding.all(16)
        self.add_child(self._layout)

        # Prompt label
        if self._prompt:
            self._prompt_label = Label(self._prompt)
            self._prompt_label.margin.bottom = 12
            self._layout.add_child(self._prompt_label)

        # Choice buttons
        self._buttons: List[Button] = []
        for i, choice in enumerate(self._choices):
            button = Button(choice)
            button.set_on_click(lambda idx=i: self._on_choice_selected(idx))
            button.rect.width = max(120, len(choice) * 10 + 40)
            self._buttons.append(button)
            self._layout.add_child(button)

        # Calculate size
        self._layout.fit_content = True
        self._layout.layout()

        pref_w, pref_h = self._layout.get_preferred_size()
        self.rect.width = max(200, pref_w)
        self.rect.height = pref_h

    def set_prompt(self, prompt: str) -> 'ChoiceMenu':
        """Set prompt text."""
        self._prompt = prompt
        self._build_ui()
        return self

    def set_choices(self, choices: List[str]) -> 'ChoiceMenu':
        """Set choice options."""
        self._choices = choices
        self._build_ui()
        return self

    def set_allow_cancel(self, allow: bool) -> 'ChoiceMenu':
        """Set whether cancel is allowed."""
        self._allow_cancel = allow
        return self

    def _on_choice_selected(self, index: int) -> None:
        """Handle choice selection."""
        if self.on_select:
            self.on_select(index, self._choices[index])

        # Auto-close
        if self.manager:
            self.manager.pop_modal()

    # Input

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """Navigate between choices."""
        if self._layout:
            return self._layout.navigate(row_delta, col_delta)
        return False

    def on_confirm(self) -> bool:
        """Confirm current selection."""
        if self._layout:
            return self._layout.on_confirm()
        return False

    def on_cancel(self) -> bool:
        """Handle cancel."""
        if not self._allow_cancel:
            return False

        if self.on_cancel:
            self.on_cancel()

        if self.manager:
            self.manager.pop_modal()

        return True

    def focus(self) -> bool:
        """Focus and select first option."""
        if super().focus():
            if self._layout:
                self._layout.focus_first()
            return True
        return False

    # Rendering

    def render(self, renderer: 'UIRenderer') -> None:
        """Render the choice menu."""
        x, y = self.absolute_position
        theme = self.theme

        # Background with shadow
        shadow_offset = 4
        renderer.draw_rect(
            x + shadow_offset, y + shadow_offset,
            self.rect.width, self.rect.height,
            theme.colors.shadow
        )

        # Main background
        renderer.draw_rect(
            x, y, self.rect.width, self.rect.height,
            theme.colors.bg_primary
        )

        # Border
        renderer.draw_rect_outline(
            x, y, self.rect.width, self.rect.height,
            theme.colors.border_normal,
            thickness=2
        )

        # Render children
        super().render(renderer)

    @classmethod
    def yes_no(
        cls,
        prompt: str,
        on_yes: Optional[Callable[[], None]] = None,
        on_no: Optional[Callable[[], None]] = None,
    ) -> 'ChoiceMenu':
        """Create a Yes/No dialog."""
        menu = cls(prompt, ["Yes", "No"])

        def on_select(index: int, choice: str) -> None:
            if index == 0 and on_yes:
                on_yes()
            elif index == 1 and on_no:
                on_no()

        menu.on_select = on_select
        menu.on_cancel = on_no  # Cancel = No
        return menu

    @classmethod
    def confirm(
        cls,
        prompt: str,
        on_confirm: Optional[Callable[[], None]] = None,
    ) -> 'ChoiceMenu':
        """Create a simple confirmation dialog."""
        menu = cls(prompt, ["OK"])
        menu.on_select = lambda idx, choice: on_confirm() if on_confirm else None
        menu.set_allow_cancel(True)
        return menu
