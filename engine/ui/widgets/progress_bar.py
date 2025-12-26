"""
Progress bar widget for HP/MP bars and loading indicators.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

from engine.ui.widget import Widget
from engine.ui.renderer import FontConfig

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


class ProgressBar(Widget):
    """
    Progress bar widget for displaying values.

    Features:
    - Smooth animation
    - Custom colors
    - Optional text label
    - Segmented or smooth fill
    - Various presets (HP, MP, EXP)
    """

    def __init__(
        self,
        value: float = 1.0,
        max_value: float = 1.0,
    ):
        super().__init__()
        self._value = value
        self._max_value = max_value
        self._display_value = value  # For animation

        # Visual options
        self.show_text: bool = False
        self.text_format: str = "{value}/{max}"  # Or "{percent}%"
        self.bar_color: Optional[Tuple[int, ...]] = None
        self.bg_color: Optional[Tuple[int, ...]] = None
        self.border_color: Optional[Tuple[int, ...]] = None

        # Animation
        self.animate: bool = True
        self.animation_speed: float = 3.0  # Per second

        # Segmented display
        self.segmented: bool = False
        self.segment_count: int = 10

        # Default size
        self.rect.width = 100
        self.rect.height = 16

        # Not focusable
        self.focusable = False

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, val: float) -> None:
        self._value = max(0, min(val, self._max_value))
        if not self.animate:
            self._display_value = self._value

    @property
    def max_value(self) -> float:
        return self._max_value

    @max_value.setter
    def max_value(self, val: float) -> None:
        self._max_value = max(0, val)
        self._value = min(self._value, self._max_value)

    @property
    def percent(self) -> float:
        """Get value as percentage (0-1)."""
        if self._max_value <= 0:
            return 0
        return self._value / self._max_value

    @property
    def display_percent(self) -> float:
        """Get animated display percentage."""
        if self._max_value <= 0:
            return 0
        return self._display_value / self._max_value

    def set_value(self, value: float, max_value: Optional[float] = None) -> 'ProgressBar':
        """Set value and optionally max value (fluent)."""
        if max_value is not None:
            self.max_value = max_value
        self.value = value
        return self

    def set_bar_color(self, color: Tuple[int, ...]) -> 'ProgressBar':
        """Set bar fill color (fluent)."""
        self.bar_color = color
        return self

    def set_show_text(self, show: bool) -> 'ProgressBar':
        """Set text visibility (fluent)."""
        self.show_text = show
        return self

    def fill(self) -> 'ProgressBar':
        """Fill to max value."""
        self.value = self._max_value
        return self

    def empty(self) -> 'ProgressBar':
        """Empty to zero."""
        self.value = 0
        return self

    # Presets

    @classmethod
    def hp_bar(cls, current: float, max_hp: float) -> 'ProgressBar':
        """Create an HP bar preset."""
        bar = cls(current, max_hp)
        bar.bar_color = (80, 200, 80)
        bar.show_text = True
        bar.text_format = "{value}/{max}"
        return bar

    @classmethod
    def mp_bar(cls, current: float, max_mp: float) -> 'ProgressBar':
        """Create an MP bar preset."""
        bar = cls(current, max_mp)
        bar.bar_color = (80, 120, 220)
        bar.show_text = True
        bar.text_format = "{value}/{max}"
        return bar

    @classmethod
    def exp_bar(cls, current: float, needed: float) -> 'ProgressBar':
        """Create an EXP bar preset."""
        bar = cls(current, needed)
        bar.bar_color = (220, 180, 80)
        bar.show_text = True
        bar.text_format = "{percent}%"
        bar.rect.height = 12
        return bar

    # Lifecycle

    def update(self, dt: float) -> None:
        """Update animation."""
        if self.animate and self._display_value != self._value:
            diff = self._value - self._display_value
            change = self.animation_speed * self._max_value * dt

            if abs(diff) <= change:
                self._display_value = self._value
            elif diff > 0:
                self._display_value += change
            else:
                self._display_value -= change

    def render(self, renderer: 'UIRenderer') -> None:
        """Render the progress bar."""
        x, y = self.absolute_position
        theme = self.theme
        w = self.rect.width
        h = self.rect.height

        # Colors
        bg = self.bg_color or theme.colors.bg_tertiary
        border = self.border_color or theme.colors.border_normal
        fill = self.bar_color or theme.colors.accent_primary

        # Background
        renderer.draw_rect(x, y, w, h, bg)

        # Fill
        fill_width = w * self.display_percent

        if self.segmented and self.segment_count > 0:
            # Segmented fill
            segment_width = w / self.segment_count
            filled_segments = int(self.display_percent * self.segment_count)

            for i in range(filled_segments):
                seg_x = x + i * segment_width + 1
                seg_w = segment_width - 2
                renderer.draw_rect(seg_x, y + 1, seg_w, h - 2, fill)
        else:
            # Smooth fill
            if fill_width > 0:
                renderer.draw_rect(x + 1, y + 1, fill_width - 2, h - 2, fill)

        # Border
        renderer.draw_rect_outline(x, y, w, h, border)

        # Text
        if self.show_text:
            text = self._format_text()
            font_config = FontConfig(
                name=theme.fonts.family,
                size=min(theme.fonts.size_small, int(h - 4)),
            )

            # Shadow
            renderer.draw_text(
                text,
                x + w / 2 + 1, y + (h - font_config.size) / 2 + 1,
                color=(0, 0, 0),
                font_config=font_config,
                align="center"
            )
            # Text
            renderer.draw_text(
                text,
                x + w / 2, y + (h - font_config.size) / 2,
                color=theme.colors.text_primary,
                font_config=font_config,
                align="center"
            )

    def _format_text(self) -> str:
        """Format display text."""
        text = self.text_format
        text = text.replace("{value}", str(int(self._value)))
        text = text.replace("{max}", str(int(self._max_value)))
        text = text.replace("{percent}", str(int(self.percent * 100)))
        return text

    def get_preferred_size(self) -> Tuple[float, float]:
        """Get preferred size."""
        return (self.rect.width, self.rect.height)
