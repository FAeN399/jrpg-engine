"""
Dialog box preset - RPG-style text dialog.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable

from engine.ui.container import Container
from engine.ui.widgets.text_box import TextBox
from engine.ui.widgets.label import Label

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


class DialogBox(Container):
    """
    RPG-style dialog box with typewriter effect.

    Features:
    - Typewriter text reveal
    - Speaker name display
    - Portrait support
    - Auto-advance option
    - Customizable position
    """

    def __init__(
        self,
        width: float = 600,
        height: float = 140,
        position: str = "bottom",  # "top", "center", "bottom"
    ):
        super().__init__()

        # Default to bottom of screen
        self._position_mode = position
        self.rect.width = width
        self.rect.height = height

        # Create text box
        self._text_box = TextBox(width - 32, height - 32)
        self._text_box.set_position(16, 16)
        self.add_child(self._text_box)

        # Callbacks
        self.on_complete: Optional[Callable[[], None]] = None
        self.on_advance: Optional[Callable[[], None]] = None

        # Auto-advance settings
        self.auto_advance: bool = False
        self.auto_advance_delay: float = 2.0
        self._auto_timer: float = 0.0

        # Focusable
        self.focusable = True

    @property
    def text_box(self) -> TextBox:
        """Access underlying text box."""
        return self._text_box

    @property
    def is_complete(self) -> bool:
        """Check if all text has been shown."""
        return self._text_box.is_complete

    def set_text(
        self,
        text: str,
        speaker: Optional[str] = None,
        portrait: Optional[str] = None,
    ) -> 'DialogBox':
        """Set dialog text and speaker."""
        self._text_box.set_text(text, speaker, portrait)
        return self

    def set_position_mode(self, mode: str) -> 'DialogBox':
        """Set screen position: 'top', 'center', 'bottom'."""
        self._position_mode = mode
        return self

    def set_auto_advance(self, enabled: bool, delay: float = 2.0) -> 'DialogBox':
        """Enable/disable auto-advance."""
        self.auto_advance = enabled
        self.auto_advance_delay = delay
        return self

    def skip(self) -> None:
        """Skip to end of current page."""
        self._text_box.skip_to_end()

    def advance(self) -> bool:
        """Advance to next page or complete."""
        result = self._text_box.advance()

        if not result and self.on_complete:
            self.on_complete()

        if result and self.on_advance:
            self.on_advance()

        return result

    # Input

    def on_confirm(self) -> bool:
        """Advance on confirm."""
        return self.advance()

    def on_cancel(self) -> bool:
        """Skip on cancel."""
        if not self._text_box.is_page_complete:
            self.skip()
            return True
        return self.advance()

    # Lifecycle

    def update(self, dt: float) -> None:
        """Update dialog state."""
        super().update(dt)

        # Auto-advance
        if self.auto_advance and self._text_box.is_page_complete:
            self._auto_timer += dt
            if self._auto_timer >= self.auto_advance_delay:
                self._auto_timer = 0
                self.advance()

    def layout(self) -> None:
        """Position based on screen position mode."""
        # This would be called with screen dimensions in a real implementation
        # For now, just ensure text box is positioned
        self._text_box.rect.x = 16
        self._text_box.rect.y = 16
        self._text_box.rect.width = self.rect.width - 32
        self._text_box.rect.height = self.rect.height - 32

    def render(self, renderer: 'UIRenderer') -> None:
        """Render the dialog box."""
        x, y = self.absolute_position
        theme = self.theme

        # Main background
        renderer.draw_rect(
            x, y, self.rect.width, self.rect.height,
            (*theme.colors.bg_primary[:3], 240)
        )

        # Border
        renderer.draw_rect_outline(
            x, y, self.rect.width, self.rect.height,
            theme.colors.border_normal,
            thickness=2
        )

        # Inner highlight
        renderer.draw_rect_outline(
            x + 2, y + 2, self.rect.width - 4, self.rect.height - 4,
            theme.colors.bg_secondary
        )

        # Render children (text box)
        super().render(renderer)

    @classmethod
    def quick_dialog(
        cls,
        text: str,
        speaker: Optional[str] = None,
        on_complete: Optional[Callable[[], None]] = None,
    ) -> 'DialogBox':
        """Create a quick dialog box."""
        dialog = cls()
        dialog.set_text(text, speaker)
        dialog.on_complete = on_complete
        return dialog
