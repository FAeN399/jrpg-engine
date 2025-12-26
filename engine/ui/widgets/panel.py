"""
Panel widget for grouping and background.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

from engine.ui.container import Container

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


class Panel(Container):
    """
    Background panel container.

    Features:
    - Solid or gradient background
    - Border with optional rounding
    - Shadow effect
    - Header/title area
    """

    def __init__(self):
        super().__init__()

        # Visual options
        self.show_background: bool = True
        self.show_border: bool = True
        self.show_shadow: bool = False

        # Custom colors (None = use theme)
        self._bg_color: Optional[Tuple[int, ...]] = None
        self._border_color: Optional[Tuple[int, ...]] = None

        # Title
        self._title: Optional[str] = None
        self.title_align: str = "left"  # "left", "center", "right"

        # Panel is focusable to manage children
        self.focusable = True

    @property
    def bg_color(self) -> Tuple[int, ...]:
        """Get background color."""
        if self._bg_color:
            return self._bg_color
        return self.theme.colors.bg_primary

    @bg_color.setter
    def bg_color(self, value: Tuple[int, ...]) -> None:
        """Set background color."""
        self._bg_color = value

    @property
    def border_color(self) -> Tuple[int, ...]:
        """Get border color."""
        if self._border_color:
            return self._border_color
        return self.theme.colors.border_normal

    @border_color.setter
    def border_color(self, value: Tuple[int, ...]) -> None:
        """Set border color."""
        self._border_color = value

    @property
    def title(self) -> Optional[str]:
        """Get panel title."""
        return self._title

    @title.setter
    def title(self, value: Optional[str]) -> None:
        """Set panel title."""
        self._title = value

    def set_title(self, title: str) -> 'Panel':
        """Set title (fluent)."""
        self.title = title
        return self

    def set_bg_color(self, color: Tuple[int, ...]) -> 'Panel':
        """Set background color (fluent)."""
        self.bg_color = color
        return self

    def set_border_color(self, color: Tuple[int, ...]) -> 'Panel':
        """Set border color (fluent)."""
        self.border_color = color
        return self

    def set_show_background(self, show: bool) -> 'Panel':
        """Set background visibility (fluent)."""
        self.show_background = show
        return self

    def set_show_border(self, show: bool) -> 'Panel':
        """Set border visibility (fluent)."""
        self.show_border = show
        return self

    def set_show_shadow(self, show: bool) -> 'Panel':
        """Set shadow visibility (fluent)."""
        self.show_shadow = show
        return self

    def render(self, renderer: 'UIRenderer') -> None:
        """Render the panel and children."""
        x, y = self.absolute_position
        theme = self.theme
        spacing = theme.spacing

        # Draw shadow
        if self.show_shadow:
            shadow_offset = 4
            shadow_color = theme.colors.shadow
            renderer.draw_rect(
                x + shadow_offset, y + shadow_offset,
                self.rect.width, self.rect.height,
                shadow_color
            )

        # Draw background
        if self.show_background:
            if spacing.border_radius > 0:
                renderer.draw_rounded_rect(
                    x, y, self.rect.width, self.rect.height,
                    self.bg_color,
                    radius=int(spacing.border_radius)
                )
            else:
                renderer.draw_rect(
                    x, y, self.rect.width, self.rect.height,
                    self.bg_color
                )

        # Draw border
        if self.show_border:
            if spacing.border_radius > 0:
                renderer.draw_rounded_rect_outline(
                    x, y, self.rect.width, self.rect.height,
                    self.border_color,
                    thickness=int(spacing.border_width),
                    radius=int(spacing.border_radius)
                )
            else:
                renderer.draw_rect_outline(
                    x, y, self.rect.width, self.rect.height,
                    self.border_color,
                    thickness=int(spacing.border_width)
                )

        # Draw title
        if self._title:
            title_height = theme.fonts.size_large + spacing.padding_sm * 2
            title_bg = theme.colors.bg_secondary

            # Title background
            renderer.draw_rect(
                x + 1, y + 1,
                self.rect.width - 2, title_height,
                title_bg
            )

            # Title separator line
            renderer.draw_line(
                x, y + title_height,
                x + self.rect.width, y + title_height,
                self.border_color
            )

            # Title text
            if self.title_align == "center":
                title_x = x + self.rect.width / 2
            elif self.title_align == "right":
                title_x = x + self.rect.width - spacing.padding_md
            else:
                title_x = x + spacing.padding_md

            from engine.ui.renderer import FontConfig
            title_font = FontConfig(
                name=theme.fonts.family,
                size=theme.fonts.size_large,
                bold=True,
            )
            renderer.draw_text(
                self._title,
                title_x,
                y + spacing.padding_sm,
                color=theme.colors.text_accent,
                font_config=title_font,
                align=self.title_align
            )

        # Render children
        super().render(renderer)
