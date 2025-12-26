"""
Input field widget for text entry (naming, etc).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable

from engine.ui.widget import Widget
from engine.ui.renderer import FontConfig

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


class InputField(Widget):
    """
    Text input field widget.

    Features:
    - Keyboard text input
    - Cursor display
    - Max length limit
    - Placeholder text
    - Input validation
    """

    def __init__(
        self,
        placeholder: str = "",
        max_length: int = 32,
    ):
        super().__init__()
        self._text = ""
        self._placeholder = placeholder
        self._max_length = max_length

        # Cursor
        self._cursor_pos = 0
        self._cursor_visible = True
        self._cursor_timer = 0.0

        # Selection (for future use)
        self._selection_start = 0
        self._selection_end = 0

        # Callbacks
        self.on_change: Optional[Callable[[str], None]] = None
        self.on_submit: Optional[Callable[[str], None]] = None
        self.on_cancel: Optional[Callable[[], None]] = None

        # Validation
        self.allowed_chars: Optional[str] = None  # None = all printable
        self.validate: Optional[Callable[[str], bool]] = None

        # Visual
        self._active = False

        # Default size
        self.rect.width = 200
        self.rect.height = 32

        # Focusable
        self.focusable = True

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        if len(value) <= self._max_length:
            self._text = value
            self._cursor_pos = min(self._cursor_pos, len(value))

    @property
    def placeholder(self) -> str:
        return self._placeholder

    @placeholder.setter
    def placeholder(self, value: str) -> None:
        self._placeholder = value

    def set_text(self, text: str) -> 'InputField':
        """Set text (fluent)."""
        self.text = text
        return self

    def set_placeholder(self, placeholder: str) -> 'InputField':
        """Set placeholder (fluent)."""
        self.placeholder = placeholder
        return self

    def set_max_length(self, length: int) -> 'InputField':
        """Set max length (fluent)."""
        self._max_length = length
        return self

    def clear(self) -> None:
        """Clear the input field."""
        self._text = ""
        self._cursor_pos = 0
        if self.on_change:
            self.on_change("")

    # Text manipulation

    def insert_char(self, char: str) -> bool:
        """Insert a character at cursor position."""
        if len(self._text) >= self._max_length:
            return False

        # Validate character
        if self.allowed_chars and char not in self.allowed_chars:
            return False

        # Insert
        new_text = self._text[:self._cursor_pos] + char + self._text[self._cursor_pos:]

        # Validate full text
        if self.validate and not self.validate(new_text):
            return False

        self._text = new_text
        self._cursor_pos += 1

        if self.on_change:
            self.on_change(self._text)

        return True

    def delete_char(self, forward: bool = False) -> bool:
        """Delete character before (backspace) or after (delete) cursor."""
        if forward:
            if self._cursor_pos >= len(self._text):
                return False
            self._text = self._text[:self._cursor_pos] + self._text[self._cursor_pos + 1:]
        else:
            if self._cursor_pos <= 0:
                return False
            self._text = self._text[:self._cursor_pos - 1] + self._text[self._cursor_pos:]
            self._cursor_pos -= 1

        if self.on_change:
            self.on_change(self._text)

        return True

    def move_cursor(self, delta: int) -> None:
        """Move cursor by delta."""
        self._cursor_pos = max(0, min(len(self._text), self._cursor_pos + delta))
        self._cursor_visible = True
        self._cursor_timer = 0

    # Focus

    def focus(self) -> bool:
        """Activate input field."""
        if super().focus():
            self._active = True
            self._cursor_visible = True
            self._cursor_timer = 0
            return True
        return False

    def unfocus(self) -> None:
        """Deactivate input field."""
        super().unfocus()
        self._active = False

    # Input

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """Handle cursor navigation."""
        if col_delta != 0:
            self.move_cursor(col_delta)
            return True
        return False

    def on_confirm(self) -> bool:
        """Handle submit."""
        if self.on_submit:
            self.on_submit(self._text)
        return True

    def handle_key(self, key: int) -> bool:
        """
        Handle keyboard input.

        This should be called from the UI manager with pygame key constants.
        """
        import pygame

        if key == pygame.K_BACKSPACE:
            return self.delete_char(forward=False)
        elif key == pygame.K_DELETE:
            return self.delete_char(forward=True)
        elif key == pygame.K_LEFT:
            self.move_cursor(-1)
            return True
        elif key == pygame.K_RIGHT:
            self.move_cursor(1)
            return True
        elif key == pygame.K_HOME:
            self._cursor_pos = 0
            return True
        elif key == pygame.K_END:
            self._cursor_pos = len(self._text)
            return True

        return False

    def handle_text_input(self, text: str) -> bool:
        """Handle text input event."""
        for char in text:
            if char.isprintable():
                if not self.insert_char(char):
                    return False
        return True

    # Lifecycle

    def update(self, dt: float) -> None:
        """Update cursor blink."""
        if self._active:
            self._cursor_timer += dt
            if self._cursor_timer >= 0.5:
                self._cursor_timer = 0
                self._cursor_visible = not self._cursor_visible

    def render(self, renderer: 'UIRenderer') -> None:
        """Render the input field."""
        x, y = self.absolute_position
        theme = self.theme
        spacing = theme.spacing

        # Background
        if self._active:
            bg_color = theme.colors.bg_secondary
            border_color = theme.colors.border_focus
        else:
            bg_color = theme.colors.bg_tertiary
            border_color = theme.colors.border_normal

        renderer.draw_rect(x, y, self.rect.width, self.rect.height, bg_color)
        renderer.draw_rect_outline(x, y, self.rect.width, self.rect.height, border_color)

        # Text or placeholder
        font_config = FontConfig(
            name=theme.fonts.family,
            size=theme.fonts.size_normal,
        )

        text_x = x + spacing.padding_md
        text_y = y + (self.rect.height - theme.fonts.size_normal) / 2

        if self._text:
            renderer.draw_text(
                self._text,
                text_x, text_y,
                color=theme.colors.text_primary,
                font_config=font_config
            )
        elif self._placeholder:
            renderer.draw_text(
                self._placeholder,
                text_x, text_y,
                color=theme.colors.text_muted,
                font_config=font_config
            )

        # Cursor
        if self._active and self._cursor_visible:
            # Measure text up to cursor
            text_before_cursor = self._text[:self._cursor_pos]
            cursor_x = text_x + len(text_before_cursor) * theme.fonts.size_normal * 0.6

            renderer.draw_line(
                cursor_x, y + 4,
                cursor_x, y + self.rect.height - 4,
                theme.colors.text_primary,
                thickness=2
            )

    def get_preferred_size(self) -> tuple[float, float]:
        """Get preferred size."""
        theme = self.theme
        width = self._max_length * theme.fonts.size_normal * 0.6 + theme.spacing.padding_md * 2
        height = theme.spacing.input_height
        return (min(width, 300), height)
