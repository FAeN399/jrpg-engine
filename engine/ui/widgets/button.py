"""
Button widget for selectable actions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable, Tuple

from engine.ui.widget import Widget
from engine.ui.renderer import FontConfig

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


class Button(Widget):
    """
    Selectable button widget.

    Features:
    - Text label with optional icon
    - Keyboard/gamepad selection
    - Mouse hover and click
    - Disabled state
    - Visual feedback for focus and press
    """

    def __init__(
        self,
        text: str = "",
        on_click: Optional[Callable[[], None]] = None,
    ):
        super().__init__()
        self._text = text
        self.on_click = on_click

        # Visual options
        self.icon: Optional[str] = None  # Icon path (left of text)
        self.icon_right: Optional[str] = None  # Icon path (right of text)

        # State
        self._hover = False
        self._press_timer = 0.0

        # Button is focusable
        self.focusable = True

        # Default size
        self.rect.width = 120
        self.rect.height = 32

    @property
    def text(self) -> str:
        """Get button text."""
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        """Set button text."""
        self._text = value

    def set_text(self, text: str) -> 'Button':
        """Set text (fluent)."""
        self.text = text
        return self

    def set_on_click(self, callback: Callable[[], None]) -> 'Button':
        """Set click callback (fluent)."""
        self.on_click = callback
        return self

    def set_icon(self, path: str) -> 'Button':
        """Set left icon (fluent)."""
        self.icon = path
        return self

    # Input handling

    def on_confirm(self) -> bool:
        """Handle button press."""
        if not self.enabled:
            return False

        self._press_timer = 0.15  # Visual feedback duration

        if self.on_click:
            self.on_click()

        return True

    def on_mouse_enter(self) -> None:
        """Handle mouse hover start."""
        self._hover = True

    def on_mouse_exit(self) -> None:
        """Handle mouse hover end."""
        self._hover = False

    def on_mouse_down(self, x: float, y: float, button: int) -> bool:
        """Handle mouse click."""
        if button == 1:  # Left click
            return self.on_confirm()
        return False

    # Lifecycle

    def update(self, dt: float) -> None:
        """Update press animation."""
        if self._press_timer > 0:
            self._press_timer -= dt

    def render(self, renderer: 'UIRenderer') -> None:
        """Render the button."""
        x, y = self.absolute_position
        theme = self.theme
        spacing = theme.spacing

        # Determine colors based on state
        if not self.enabled:
            bg_color = theme.colors.bg_disabled
            text_color = theme.colors.text_disabled
            border_color = theme.colors.border_normal
        elif self._press_timer > 0:
            bg_color = theme.colors.bg_active
            text_color = theme.colors.text_primary
            border_color = theme.colors.border_active
        elif self.focused:
            bg_color = theme.colors.bg_hover
            text_color = theme.colors.text_primary
            border_color = theme.colors.border_focus
        elif self._hover:
            bg_color = theme.colors.bg_hover
            text_color = theme.colors.text_primary
            border_color = theme.colors.border_normal
        else:
            bg_color = theme.colors.bg_secondary
            text_color = theme.colors.text_secondary
            border_color = theme.colors.border_normal

        # Draw background
        if spacing.border_radius > 0:
            renderer.draw_rounded_rect(
                x, y, self.rect.width, self.rect.height,
                bg_color,
                radius=int(spacing.border_radius)
            )
        else:
            renderer.draw_rect(
                x, y, self.rect.width, self.rect.height,
                bg_color
            )

        # Draw border
        if self.focused or self._hover:
            if spacing.border_radius > 0:
                renderer.draw_rounded_rect_outline(
                    x, y, self.rect.width, self.rect.height,
                    border_color,
                    thickness=int(spacing.border_width),
                    radius=int(spacing.border_radius)
                )
            else:
                renderer.draw_rect_outline(
                    x, y, self.rect.width, self.rect.height,
                    border_color,
                    thickness=int(spacing.border_width)
                )

        # Draw focus indicator
        if self.focused and spacing.focus_ring_width > 0:
            offset = spacing.focus_ring_offset
            renderer.draw_rect_outline(
                x - offset, y - offset,
                self.rect.width + offset * 2, self.rect.height + offset * 2,
                theme.colors.focus_ring,
                thickness=int(spacing.focus_ring_width)
            )

        # Calculate text position
        text_x = x + self.rect.width / 2
        text_y = y + self.rect.height / 2 - theme.fonts.size_normal / 2

        # Draw icon if present
        if self.icon:
            icon_size = spacing.icon_size
            icon_x = x + spacing.padding_md
            icon_y = y + (self.rect.height - icon_size) / 2
            renderer.draw_sprite(self.icon, icon_x, icon_y, icon_size, icon_size)
            # Shift text to the right
            text_x = x + spacing.padding_md + icon_size + spacing.padding_sm + \
                     (self.rect.width - spacing.padding_md - icon_size - spacing.padding_sm) / 2

        # Draw text
        font_config = FontConfig(
            name=theme.fonts.family,
            size=theme.fonts.size_normal,
        )
        renderer.draw_text(
            self._text,
            text_x,
            text_y,
            color=text_color,
            font_config=font_config,
            align="center"
        )

    def get_preferred_size(self) -> Tuple[float, float]:
        """Get preferred size based on text."""
        theme = self.theme
        char_width = theme.fonts.size_normal * 0.6
        text_width = len(self._text) * char_width

        width = max(
            theme.spacing.button_min_width,
            text_width + theme.spacing.padding_lg * 2
        )

        if self.icon:
            width += theme.spacing.icon_size + theme.spacing.padding_sm

        height = theme.spacing.button_height

        return (width, height)
