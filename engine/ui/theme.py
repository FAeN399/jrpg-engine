"""
UI Theming system.

Provides consistent colors, fonts, and spacing for UI widgets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, Any


# Type aliases
Color = Tuple[int, int, int] | Tuple[int, int, int, int]


@dataclass
class ColorPalette:
    """Color scheme for UI elements."""

    # Backgrounds
    bg_primary: Color = (30, 30, 50)
    bg_secondary: Color = (45, 45, 70)
    bg_tertiary: Color = (60, 60, 90)
    bg_hover: Color = (70, 70, 100)
    bg_active: Color = (80, 100, 140)
    bg_disabled: Color = (40, 40, 50)

    # Text
    text_primary: Color = (255, 255, 255)
    text_secondary: Color = (180, 180, 200)
    text_muted: Color = (120, 120, 140)
    text_disabled: Color = (80, 80, 100)
    text_accent: Color = (255, 220, 100)
    text_error: Color = (255, 100, 100)
    text_success: Color = (100, 255, 150)

    # Borders
    border_normal: Color = (100, 100, 140)
    border_focus: Color = (150, 150, 200)
    border_active: Color = (200, 200, 255)
    border_error: Color = (255, 100, 100)

    # Accents
    accent_primary: Color = (80, 120, 200)
    accent_secondary: Color = (100, 180, 120)
    accent_warning: Color = (220, 180, 80)
    accent_danger: Color = (200, 80, 80)

    # Focus indicator
    focus_ring: Color = (255, 255, 255, 200)
    focus_glow: Color = (100, 150, 255, 100)

    # Shadows
    shadow: Color = (0, 0, 0, 128)


@dataclass
class FontSettings:
    """Font configuration for UI."""

    # Font family (None = system default)
    family: Optional[str] = None

    # Sizes
    size_small: int = 12
    size_normal: int = 16
    size_large: int = 20
    size_header: int = 24
    size_title: int = 32


@dataclass
class Spacing:
    """Spacing and sizing constants."""

    # Padding
    padding_xs: float = 2
    padding_sm: float = 4
    padding_md: float = 8
    padding_lg: float = 16
    padding_xl: float = 24

    # Margins
    margin_xs: float = 2
    margin_sm: float = 4
    margin_md: float = 8
    margin_lg: float = 16
    margin_xl: float = 24

    # Widget sizing
    button_height: float = 32
    button_min_width: float = 80
    input_height: float = 28
    list_item_height: float = 28
    icon_size: float = 16
    icon_size_lg: float = 24

    # Borders
    border_width: float = 1
    border_radius: float = 4

    # Focus
    focus_ring_width: float = 2
    focus_ring_offset: float = 2


@dataclass
class AnimationSettings:
    """Animation timing settings."""

    # Durations (seconds)
    duration_fast: float = 0.1
    duration_normal: float = 0.2
    duration_slow: float = 0.4

    # Typewriter
    chars_per_second: int = 30
    chars_per_second_fast: int = 60

    # Transitions
    fade_duration: float = 0.3
    slide_duration: float = 0.2


@dataclass
class Theme:
    """
    Complete UI theme.

    Themes define the visual appearance of all UI elements.
    """

    name: str = "default"
    colors: ColorPalette = field(default_factory=ColorPalette)
    fonts: FontSettings = field(default_factory=FontSettings)
    spacing: Spacing = field(default_factory=Spacing)
    animation: AnimationSettings = field(default_factory=AnimationSettings)

    # Custom properties for specific widgets
    custom: Dict[str, Any] = field(default_factory=dict)

    def with_colors(self, **kwargs) -> 'Theme':
        """Create a copy with modified colors."""
        new_colors = ColorPalette(**{**self.colors.__dict__, **kwargs})
        return Theme(
            name=self.name,
            colors=new_colors,
            fonts=self.fonts,
            spacing=self.spacing,
            animation=self.animation,
            custom=self.custom.copy(),
        )

    def with_fonts(self, **kwargs) -> 'Theme':
        """Create a copy with modified fonts."""
        new_fonts = FontSettings(**{**self.fonts.__dict__, **kwargs})
        return Theme(
            name=self.name,
            colors=self.colors,
            fonts=new_fonts,
            spacing=self.spacing,
            animation=self.animation,
            custom=self.custom.copy(),
        )


# Default theme instance
DEFAULT_THEME = Theme(name="default")


# Dark theme variant
DARK_THEME = Theme(
    name="dark",
    colors=ColorPalette(
        bg_primary=(20, 20, 30),
        bg_secondary=(30, 30, 45),
        bg_tertiary=(40, 40, 60),
        bg_hover=(50, 50, 75),
        bg_active=(60, 80, 120),
        bg_disabled=(25, 25, 35),
        text_primary=(240, 240, 255),
        text_secondary=(170, 170, 190),
        text_muted=(100, 100, 120),
        text_disabled=(70, 70, 85),
        border_normal=(80, 80, 110),
        border_focus=(120, 120, 160),
        accent_primary=(70, 110, 180),
    ),
)


# Light theme variant
LIGHT_THEME = Theme(
    name="light",
    colors=ColorPalette(
        bg_primary=(240, 240, 245),
        bg_secondary=(225, 225, 235),
        bg_tertiary=(210, 210, 220),
        bg_hover=(200, 200, 215),
        bg_active=(180, 200, 230),
        bg_disabled=(220, 220, 225),
        text_primary=(30, 30, 40),
        text_secondary=(70, 70, 85),
        text_muted=(120, 120, 135),
        text_disabled=(160, 160, 170),
        text_accent=(180, 140, 40),
        border_normal=(180, 180, 195),
        border_focus=(140, 140, 160),
        accent_primary=(80, 120, 200),
    ),
)


# Classic JRPG theme (Final Fantasy style)
JRPG_CLASSIC_THEME = Theme(
    name="jrpg_classic",
    colors=ColorPalette(
        bg_primary=(0, 0, 128),        # Deep blue
        bg_secondary=(32, 32, 160),
        bg_tertiary=(64, 64, 192),
        bg_hover=(48, 48, 176),
        bg_active=(80, 80, 200),
        bg_disabled=(16, 16, 96),
        text_primary=(255, 255, 255),
        text_secondary=(200, 200, 255),
        text_muted=(150, 150, 200),
        text_accent=(255, 255, 128),   # Yellow for important text
        border_normal=(128, 128, 255),
        border_focus=(192, 192, 255),
        border_active=(255, 255, 255),
        accent_primary=(128, 128, 255),
    ),
    spacing=Spacing(
        border_width=2,
        border_radius=0,  # Sharp corners for retro look
        button_height=28,
        list_item_height=24,
    ),
)


# Register themes
THEMES: Dict[str, Theme] = {
    "default": DEFAULT_THEME,
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
    "jrpg_classic": JRPG_CLASSIC_THEME,
}


def get_theme(name: str) -> Theme:
    """Get a theme by name."""
    return THEMES.get(name, DEFAULT_THEME)


def register_theme(theme: Theme) -> None:
    """Register a custom theme."""
    THEMES[theme.name] = theme
