"""
Image widget for displaying sprites and images.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

import pygame

from engine.ui.widget import Widget

if TYPE_CHECKING:
    from engine.ui.renderer import UIRenderer


class Image(Widget):
    """
    Image/sprite display widget.

    Features:
    - Load from file path
    - Display pygame Surface directly
    - Scaling options
    - Tint color
    """

    def __init__(
        self,
        path: Optional[str] = None,
        surface: Optional[pygame.Surface] = None,
    ):
        super().__init__()
        self._path = path
        self._surface = surface
        self._loaded_surface: Optional[pygame.Surface] = None

        # Display options
        self.scale_mode: str = "none"  # "none", "fit", "fill", "stretch"
        self.tint: Optional[Tuple[int, ...]] = None
        self.alpha: float = 1.0

        # Not focusable by default
        self.focusable = False

        # Load image if path provided
        if path:
            self._load_image(path)

    @property
    def path(self) -> Optional[str]:
        """Get image path."""
        return self._path

    @path.setter
    def path(self, value: str) -> None:
        """Set image path and load."""
        self._path = value
        self._load_image(value)

    @property
    def surface(self) -> Optional[pygame.Surface]:
        """Get the display surface."""
        return self._surface or self._loaded_surface

    @surface.setter
    def surface(self, value: pygame.Surface) -> None:
        """Set surface directly."""
        self._surface = value
        self._loaded_surface = None
        self._update_size_from_surface()

    def _load_image(self, path: str) -> bool:
        """Load image from path."""
        try:
            self._loaded_surface = pygame.image.load(path).convert_alpha()
            self._update_size_from_surface()
            return True
        except pygame.error:
            self._loaded_surface = None
            return False

    def _update_size_from_surface(self) -> None:
        """Update widget size from loaded surface."""
        surface = self.surface
        if surface and self.rect.width == 0 and self.rect.height == 0:
            self.rect.width = surface.get_width()
            self.rect.height = surface.get_height()

    def set_path(self, path: str) -> 'Image':
        """Set image path (fluent)."""
        self.path = path
        return self

    def set_surface(self, surface: pygame.Surface) -> 'Image':
        """Set surface (fluent)."""
        self.surface = surface
        return self

    def set_scale_mode(self, mode: str) -> 'Image':
        """Set scale mode (fluent)."""
        self.scale_mode = mode
        return self

    def set_tint(self, color: Tuple[int, ...]) -> 'Image':
        """Set tint color (fluent)."""
        self.tint = color
        return self

    def get_preferred_size(self) -> Tuple[float, float]:
        """Get preferred size from image dimensions."""
        surface = self.surface
        if surface:
            return (
                surface.get_width() + self.padding.horizontal,
                surface.get_height() + self.padding.vertical
            )
        return (0, 0)

    def render(self, renderer: 'UIRenderer') -> None:
        """Render the image."""
        surface = self.surface
        if not surface:
            # Draw placeholder
            x, y = self.absolute_position
            renderer.draw_rect(
                x, y, self.rect.width, self.rect.height,
                (100, 100, 100)
            )
            renderer.draw_text("?", x + self.rect.width / 2, y + self.rect.height / 2,
                             align="center")
            return

        x, y = self.absolute_position
        x += self.padding.left
        y += self.padding.top

        # Calculate display dimensions
        content_width = self.rect.width - self.padding.horizontal
        content_height = self.rect.height - self.padding.vertical
        img_width = surface.get_width()
        img_height = surface.get_height()

        # Apply scale mode
        if self.scale_mode == "fit":
            scale = min(content_width / img_width, content_height / img_height)
            display_width = img_width * scale
            display_height = img_height * scale
            # Center
            x += (content_width - display_width) / 2
            y += (content_height - display_height) / 2
        elif self.scale_mode == "fill":
            scale = max(content_width / img_width, content_height / img_height)
            display_width = img_width * scale
            display_height = img_height * scale
        elif self.scale_mode == "stretch":
            display_width = content_width
            display_height = content_height
        else:  # "none"
            display_width = img_width
            display_height = img_height

        # Prepare surface for drawing
        display_surface = surface

        # Apply tint if needed
        if self.tint:
            display_surface = surface.copy()
            display_surface.fill(self.tint, special_flags=pygame.BLEND_MULT)

        # Apply alpha
        if self.alpha < 1.0:
            if display_surface == surface:
                display_surface = surface.copy()
            display_surface.set_alpha(int(self.alpha * 255))

        # Draw
        renderer.draw_surface(display_surface, x, y, display_width, display_height)
