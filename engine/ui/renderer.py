"""
UI Renderer for drawing primitives and text.

Provides a simple API for UI rendering that works with pygame
surfaces while the main game uses ModernGL for GPU rendering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Tuple, Optional
from pathlib import Path

import pygame

if TYPE_CHECKING:
    pass


@dataclass
class FontConfig:
    """Font configuration."""
    name: Optional[str] = None  # None = pygame default
    size: int = 16
    bold: bool = False
    italic: bool = False


class UIRenderer:
    """
    Renderer for UI elements.

    Draws directly to a pygame surface. For games using ModernGL,
    the UI surface is composited onto the final output.

    Usage:
        renderer = UIRenderer(screen_surface)
        renderer.draw_rect(10, 10, 100, 50, (50, 50, 70))
        renderer.draw_text("Hello", 60, 35, color=(255, 255, 255), align="center")
    """

    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self._fonts: dict[tuple, pygame.font.Font] = {}
        self._default_font = FontConfig()

    def set_surface(self, surface: pygame.Surface) -> None:
        """Change the target surface."""
        self.surface = surface

    def get_font(self, config: Optional[FontConfig] = None) -> pygame.font.Font:
        """Get or create a font from config."""
        if config is None:
            config = self._default_font

        key = (config.name, config.size, config.bold, config.italic)

        if key not in self._fonts:
            if config.name:
                font = pygame.font.Font(config.name, config.size)
            else:
                font = pygame.font.SysFont(None, config.size)
            font.set_bold(config.bold)
            font.set_italic(config.italic)
            self._fonts[key] = font

        return self._fonts[key]

    def draw_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: Tuple[int, ...],
    ) -> None:
        """Draw a filled rectangle."""
        rect = pygame.Rect(int(x), int(y), int(width), int(height))

        if len(color) == 4 and color[3] < 255:
            # Alpha blending needed
            temp = pygame.Surface((int(width), int(height)), pygame.SRCALPHA)
            temp.fill(color)
            self.surface.blit(temp, (int(x), int(y)))
        else:
            pygame.draw.rect(self.surface, color[:3], rect)

    def draw_rect_outline(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: Tuple[int, ...],
        thickness: int = 1,
    ) -> None:
        """Draw a rectangle outline."""
        rect = pygame.Rect(int(x), int(y), int(width), int(height))
        pygame.draw.rect(self.surface, color[:3], rect, thickness)

    def draw_rounded_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: Tuple[int, ...],
        radius: int = 4,
    ) -> None:
        """Draw a filled rounded rectangle."""
        rect = pygame.Rect(int(x), int(y), int(width), int(height))

        if len(color) == 4 and color[3] < 255:
            temp = pygame.Surface((int(width), int(height)), pygame.SRCALPHA)
            pygame.draw.rect(temp, color, temp.get_rect(), border_radius=radius)
            self.surface.blit(temp, (int(x), int(y)))
        else:
            pygame.draw.rect(self.surface, color[:3], rect, border_radius=radius)

    def draw_rounded_rect_outline(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: Tuple[int, ...],
        thickness: int = 1,
        radius: int = 4,
    ) -> None:
        """Draw a rounded rectangle outline."""
        rect = pygame.Rect(int(x), int(y), int(width), int(height))
        pygame.draw.rect(self.surface, color[:3], rect, thickness, border_radius=radius)

    def draw_line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: Tuple[int, ...],
        thickness: int = 1,
    ) -> None:
        """Draw a line."""
        pygame.draw.line(
            self.surface,
            color[:3],
            (int(x1), int(y1)),
            (int(x2), int(y2)),
            thickness
        )

    def draw_text(
        self,
        text: str,
        x: float,
        y: float,
        color: Tuple[int, ...] = (255, 255, 255),
        font_config: Optional[FontConfig] = None,
        align: str = "left",
        max_width: Optional[float] = None,
    ) -> pygame.Rect:
        """
        Draw text.

        Args:
            text: Text to render
            x, y: Position
            color: Text color (RGB or RGBA)
            font_config: Font settings
            align: "left", "center", or "right"
            max_width: Maximum width for text wrapping

        Returns:
            Bounding rect of rendered text
        """
        font = self.get_font(font_config)

        if max_width and len(text) > 0:
            # Word wrap
            lines = self._wrap_text(text, font, max_width)
        else:
            lines = [text]

        total_rect = pygame.Rect(int(x), int(y), 0, 0)
        line_height = font.get_height()

        for i, line in enumerate(lines):
            if not line:
                continue

            text_surface = font.render(line, True, color[:3])
            text_rect = text_surface.get_rect()

            # Apply alignment
            if align == "center":
                text_rect.centerx = int(x)
            elif align == "right":
                text_rect.right = int(x)
            else:
                text_rect.left = int(x)

            text_rect.top = int(y) + i * line_height

            # Alpha handling
            if len(color) == 4 and color[3] < 255:
                text_surface.set_alpha(color[3])

            self.surface.blit(text_surface, text_rect)
            total_rect = total_rect.union(text_rect)

        return total_rect

    def draw_sprite(
        self,
        sprite_path: str,
        x: float,
        y: float,
        width: Optional[float] = None,
        height: Optional[float] = None,
    ) -> None:
        """Draw a sprite image."""
        try:
            image = pygame.image.load(sprite_path)
            if width and height:
                image = pygame.transform.scale(image, (int(width), int(height)))
            self.surface.blit(image, (int(x), int(y)))
        except pygame.error:
            # Draw placeholder on error
            w = int(width) if width else 32
            h = int(height) if height else 32
            self.draw_rect(x, y, w, h, (255, 0, 255))

    def draw_surface(
        self,
        source: pygame.Surface,
        x: float,
        y: float,
        width: Optional[float] = None,
        height: Optional[float] = None,
    ) -> None:
        """Draw a pygame surface."""
        if width and height:
            source = pygame.transform.scale(source, (int(width), int(height)))
        self.surface.blit(source, (int(x), int(y)))

    def measure_text(
        self,
        text: str,
        font_config: Optional[FontConfig] = None,
    ) -> Tuple[int, int]:
        """Measure text dimensions."""
        font = self.get_font(font_config)
        return font.size(text)

    def get_line_height(self, font_config: Optional[FontConfig] = None) -> int:
        """Get font line height."""
        font = self.get_font(font_config)
        return font.get_height()

    def _wrap_text(
        self,
        text: str,
        font: pygame.font.Font,
        max_width: float,
    ) -> list[str]:
        """Wrap text to fit within max_width."""
        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word

            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines if lines else [""]

    def set_clip(self, x: float, y: float, width: float, height: float) -> None:
        """Set clipping rectangle."""
        self.surface.set_clip(pygame.Rect(int(x), int(y), int(width), int(height)))

    def clear_clip(self) -> None:
        """Clear clipping rectangle."""
        self.surface.set_clip(None)
