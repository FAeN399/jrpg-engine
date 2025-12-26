"""
Text box widget for RPG-style dialog with typewriter effect.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable, List

from engine.ui.widget import Widget
from engine.ui.renderer import FontConfig

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


class TextBox(Widget):
    """
    RPG-style text box with typewriter effect.

    Features:
    - Character-by-character reveal
    - Speed control (instant, fast, normal, slow)
    - Text sound effects
    - Page breaks for long text
    - Speaker name display
    - Portrait display
    """

    def __init__(
        self,
        width: float = 400,
        height: float = 120,
    ):
        super().__init__()
        self.rect.width = width
        self.rect.height = height

        # Text content
        self._full_text = ""
        self._visible_text = ""
        self._char_index = 0
        self._pages: List[str] = []
        self._current_page = 0

        # Typewriter effect
        self.chars_per_second: int = 30
        self._char_timer = 0.0
        self._is_page_complete = False

        # Speaker
        self._speaker_name: Optional[str] = None
        self._portrait: Optional[str] = None

        # Sound
        self.text_sound: Optional[str] = "sfx/text_blip.wav"
        self._sound_interval = 2  # Play sound every N characters

        # Callbacks
        self.on_complete: Optional[Callable[[], None]] = None
        self.on_page_advance: Optional[Callable[[], None]] = None
        self.on_text_sound: Optional[Callable[[str], None]] = None  # Callback(sound_path)

        # Visual settings
        self.max_lines: int = 3
        self.line_height: float = 24
        self.show_indicator: bool = True
        self._indicator_timer = 0.0

        # Focusable for input
        self.focusable = True

    @property
    def speaker_name(self) -> Optional[str]:
        return self._speaker_name

    @property
    def portrait(self) -> Optional[str]:
        return self._portrait

    @property
    def is_complete(self) -> bool:
        """True if all text (including all pages) has been shown."""
        return (
            self._is_page_complete and
            self._current_page >= len(self._pages) - 1
        )

    @property
    def is_page_complete(self) -> bool:
        """True if current page text is fully visible."""
        return self._is_page_complete

    def set_text(
        self,
        text: str,
        speaker: Optional[str] = None,
        portrait: Optional[str] = None,
    ) -> 'TextBox':
        """
        Set new text to display.

        Args:
            text: The text to display
            speaker: Optional speaker name
            portrait: Optional portrait image path
        """
        self._full_text = text
        self._speaker_name = speaker
        self._portrait = portrait

        # Reset state
        self._visible_text = ""
        self._char_index = 0
        self._is_page_complete = False
        self._char_timer = 0.0

        # Paginate text
        self._paginate()
        self._current_page = 0

        return self

    def _paginate(self) -> None:
        """Split text into pages based on max_lines."""
        # Simple pagination - split by \n\n or when exceeding max_lines
        # More sophisticated word-wrapping would go here

        paragraphs = self._full_text.split("\n\n")
        self._pages = []

        for para in paragraphs:
            if para.strip():
                self._pages.append(para.strip())

        if not self._pages:
            self._pages = [""]

    def skip_to_end(self) -> None:
        """Instantly show all text on current page."""
        if self._current_page < len(self._pages):
            self._visible_text = self._pages[self._current_page]
            self._char_index = len(self._visible_text)
            self._is_page_complete = True

    def advance(self) -> bool:
        """
        Advance text display.

        Returns:
            True if there's more content, False if fully complete
        """
        if not self._is_page_complete:
            # Skip to end of current page
            self.skip_to_end()
            return True
        elif self._current_page < len(self._pages) - 1:
            # Go to next page
            self._current_page += 1
            self._visible_text = ""
            self._char_index = 0
            self._is_page_complete = False

            if self.on_page_advance:
                self.on_page_advance()

            return True
        else:
            # All done
            if self.on_complete:
                self.on_complete()
            return False

    # Input

    def on_confirm(self) -> bool:
        """Handle confirm to advance text."""
        self.advance()
        return True

    # Lifecycle

    def update(self, dt: float) -> None:
        """Update typewriter effect."""
        # Update indicator blink
        self._indicator_timer += dt
        if self._indicator_timer >= 0.5:
            self._indicator_timer = 0.0

        # Typewriter effect
        if self._is_page_complete:
            return

        if self._current_page >= len(self._pages):
            self._is_page_complete = True
            return

        page_text = self._pages[self._current_page]

        self._char_timer += dt
        chars_to_add = int(self._char_timer * self.chars_per_second)

        if chars_to_add > 0:
            self._char_timer -= chars_to_add / self.chars_per_second

            for _ in range(chars_to_add):
                if self._char_index < len(page_text):
                    char = page_text[self._char_index]
                    self._visible_text += char
                    self._char_index += 1

                    # Play text sound at intervals for non-whitespace characters
                    if (char.strip() and
                        self._char_index % self._sound_interval == 0 and
                        self.on_text_sound and
                        self.text_sound):
                        try:
                            self.on_text_sound(self.text_sound)
                        except Exception:
                            pass  # Don't break text on sound error
                else:
                    self._is_page_complete = True
                    break

    def render(self, renderer: 'UIRenderer') -> None:
        """Render the text box."""
        x, y = self.absolute_position
        theme = self.theme
        spacing = theme.spacing

        # Background
        renderer.draw_rect(
            x, y, self.rect.width, self.rect.height,
            (*theme.colors.bg_primary[:3], 230)
        )

        # Border
        renderer.draw_rect_outline(
            x, y, self.rect.width, self.rect.height,
            theme.colors.border_normal,
            thickness=2
        )

        # Speaker name tag
        if self._speaker_name:
            name_padding = 10
            font_config = FontConfig(
                name=theme.fonts.family,
                size=theme.fonts.size_normal,
                bold=True,
            )
            name_width = len(self._speaker_name) * theme.fonts.size_normal * 0.6 + name_padding * 2

            # Name box background
            renderer.draw_rect(
                x + spacing.padding_md, y - 22,
                name_width, 22,
                theme.colors.bg_secondary
            )
            renderer.draw_rect_outline(
                x + spacing.padding_md, y - 22,
                name_width, 22,
                theme.colors.border_normal
            )

            # Name text
            renderer.draw_text(
                self._speaker_name,
                x + spacing.padding_md + name_padding,
                y - 20,
                color=theme.colors.text_accent,
                font_config=font_config
            )

        # Portrait
        text_x = x + spacing.padding_lg
        if self._portrait:
            portrait_size = 64
            portrait_margin = spacing.padding_md
            renderer.draw_sprite(
                self._portrait,
                x + portrait_margin, y + portrait_margin,
                portrait_size, portrait_size
            )
            text_x = x + portrait_size + portrait_margin * 2

        # Text
        font_config = FontConfig(
            name=theme.fonts.family,
            size=theme.fonts.size_normal,
        )
        text_y = y + spacing.padding_lg
        max_text_width = self.rect.width - (text_x - x) - spacing.padding_lg

        renderer.draw_text(
            self._visible_text,
            text_x, text_y,
            color=theme.colors.text_primary,
            font_config=font_config,
            max_width=max_text_width
        )

        # "More" indicator
        if self.show_indicator and self._is_page_complete:
            if self._indicator_timer < 0.25:  # Blink
                indicator = "..." if self._current_page < len(self._pages) - 1 else "OK"
                indicator_x = x + self.rect.width - spacing.padding_lg
                indicator_y = y + self.rect.height - spacing.padding_lg - theme.fonts.size_small

                renderer.draw_text(
                    indicator,
                    indicator_x, indicator_y,
                    color=theme.colors.text_secondary,
                    font_config=FontConfig(size=theme.fonts.size_small),
                    align="right"
                )
