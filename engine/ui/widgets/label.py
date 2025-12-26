"""
Label widget for displaying text.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

from engine.ui.widget import Widget
from engine.ui.renderer import FontConfig

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


class Label(Widget):
    """
    Simple text display widget.

    Features:
    - Single or multi-line text
    - Alignment options
    - Custom font and color
    - Auto-sizing to content
    """

    def __init__(
        self,
        text: str = "",
        color: Optional[Tuple[int, ...]] = None,
        font_size: Optional[int] = None,
    ):
        super().__init__()
        self._text = text
        self._color = color
        self._font_size = font_size
        self._font_config: Optional[FontConfig] = None

        # Alignment
        self.align: str = "left"  # "left", "center", "right"
        self.valign: str = "top"  # "top", "middle", "bottom"

        # Auto-size
        self.auto_size: bool = True

        # Wrapping
        self.max_width: Optional[float] = None

        # Not focusable by default
        self.focusable = False

    @property
    def text(self) -> str:
        """Get label text."""
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        """Set label text."""
        self._text = value
        if self.auto_size:
            self._update_size()

    @property
    def color(self) -> Tuple[int, ...]:
        """Get text color."""
        if self._color:
            return self._color
        return self.theme.colors.text_primary

    @color.setter
    def color(self, value: Tuple[int, ...]) -> None:
        """Set text color."""
        self._color = value

    @property
    def font_config(self) -> FontConfig:
        """Get font configuration."""
        if self._font_config:
            return self._font_config

        size = self._font_size or self.theme.fonts.size_normal
        return FontConfig(
            name=self.theme.fonts.family,
            size=size,
        )

    @font_config.setter
    def font_config(self, value: FontConfig) -> None:
        """Set font configuration."""
        self._font_config = value
        if self.auto_size:
            self._update_size()

    def set_text(self, text: str) -> 'Label':
        """Set text (fluent)."""
        self.text = text
        return self

    def set_color(self, color: Tuple[int, ...]) -> 'Label':
        """Set color (fluent)."""
        self.color = color
        return self

    def set_align(self, align: str) -> 'Label':
        """Set alignment (fluent)."""
        self.align = align
        return self

    def _update_size(self) -> None:
        """Update size based on text content."""
        # Would need renderer to measure - defer to render time
        pass

    def get_preferred_size(self) -> Tuple[float, float]:
        """Get preferred size based on text."""
        # Approximate without renderer
        char_width = (self._font_size or 16) * 0.6
        line_height = (self._font_size or 16) * 1.2

        lines = self._text.split('\n')
        max_line_width = max(len(line) for line in lines) if lines else 0

        width = max_line_width * char_width + self.padding.horizontal
        height = len(lines) * line_height + self.padding.vertical

        return (width, height)

    def render(self, renderer: 'UIRenderer') -> None:
        """Render the label."""
        if not self._text:
            return

        x, y = self.absolute_position

        # Calculate position based on alignment
        text_x = x + self.padding.left
        text_y = y + self.padding.top

        if self.align == "center":
            text_x = x + self.rect.width / 2
        elif self.align == "right":
            text_x = x + self.rect.width - self.padding.right

        if self.valign == "middle":
            line_height = renderer.get_line_height(self.font_config)
            text_y = y + (self.rect.height - line_height) / 2
        elif self.valign == "bottom":
            line_height = renderer.get_line_height(self.font_config)
            text_y = y + self.rect.height - line_height - self.padding.bottom

        # Determine color
        color = self.color
        if not self.enabled:
            color = self.theme.colors.text_disabled

        # Draw text
        renderer.draw_text(
            self._text,
            text_x,
            text_y,
            color=color,
            font_config=self.font_config,
            align=self.align,
            max_width=self.max_width,
        )
