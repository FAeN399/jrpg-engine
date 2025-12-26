"""
Texture and texture atlas management.

Handles loading images into GPU textures and managing
texture atlases for efficient batched rendering.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
import json

import moderngl
import pygame
import numpy as np

if TYPE_CHECKING:
    from engine.graphics.context import GraphicsContext


@dataclass
class TextureRegion:
    """
    A rectangular region within a texture.

    Used for sprite sheets, tile sets, and atlases.
    UV coordinates are normalized (0-1).
    """
    texture: moderngl.Texture
    u0: float  # Left
    v0: float  # Top
    u1: float  # Right
    v1: float  # Bottom
    width: int   # Pixel width
    height: int  # Pixel height

    @property
    def uv_coords(self) -> tuple[float, float, float, float]:
        """Get (u0, v0, u1, v1) tuple."""
        return (self.u0, self.v0, self.u1, self.v1)

    def get_uv_flipped_h(self) -> tuple[float, float, float, float]:
        """Get UVs flipped horizontally."""
        return (self.u1, self.v0, self.u0, self.v1)

    def get_uv_flipped_v(self) -> tuple[float, float, float, float]:
        """Get UVs flipped vertically."""
        return (self.u0, self.v1, self.u1, self.v0)


class TextureManager:
    """
    Manages texture loading and caching.

    Features:
    - Lazy loading with caching
    - Automatic GPU upload
    - Support for various image formats
    - Hot reload support (for editor)
    """

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self._textures: dict[str, moderngl.Texture] = {}
        self._regions: dict[str, TextureRegion] = {}

    def load(
        self,
        path: str | Path,
        filter_mode: tuple[int, int] = (moderngl.NEAREST, moderngl.NEAREST),
        generate_mipmaps: bool = False,
    ) -> moderngl.Texture:
        """
        Load a texture from file.

        Args:
            path: Path to image file
            filter_mode: (min_filter, mag_filter)
            generate_mipmaps: Whether to generate mipmaps

        Returns:
            Loaded texture
        """
        path = Path(path)
        key = str(path.resolve())

        if key in self._textures:
            return self._textures[key]

        # Load with pygame
        surface = pygame.image.load(str(path))
        texture = self._surface_to_texture(surface, filter_mode, generate_mipmaps)

        self._textures[key] = texture
        return texture

    def load_surface(
        self,
        surface: pygame.Surface,
        name: str,
        filter_mode: tuple[int, int] = (moderngl.NEAREST, moderngl.NEAREST),
    ) -> moderngl.Texture:
        """
        Create a texture from a pygame surface.

        Args:
            surface: Pygame surface
            name: Cache key
            filter_mode: Filtering mode

        Returns:
            Created texture
        """
        if name in self._textures:
            return self._textures[name]

        texture = self._surface_to_texture(surface, filter_mode)
        self._textures[name] = texture
        return texture

    def _surface_to_texture(
        self,
        surface: pygame.Surface,
        filter_mode: tuple[int, int],
        generate_mipmaps: bool = False,
    ) -> moderngl.Texture:
        """Convert pygame surface to ModernGL texture."""
        # Convert to RGBA
        if surface.get_alpha() is None:
            surface = surface.convert_alpha()

        # Get pixel data
        data = pygame.image.tostring(surface, "RGBA", True)  # Flip for OpenGL
        size = surface.get_size()

        # Create texture
        texture = self.ctx.texture(size, 4, data)
        texture.filter = filter_mode

        if generate_mipmaps:
            texture.build_mipmaps()

        return texture

    def create_empty(
        self,
        name: str,
        size: tuple[int, int],
        filter_mode: tuple[int, int] = (moderngl.NEAREST, moderngl.NEAREST),
    ) -> moderngl.Texture:
        """
        Create an empty texture.

        Args:
            name: Cache key
            size: (width, height)
            filter_mode: Filtering mode

        Returns:
            Empty texture
        """
        texture = self.ctx.texture(size, 4)
        texture.filter = filter_mode
        self._textures[name] = texture
        return texture

    def unload(self, path: str | Path) -> None:
        """Unload a texture from cache."""
        path = Path(path)
        key = str(path.resolve())

        if key in self._textures:
            self._textures[key].release()
            del self._textures[key]

    def reload(self, path: str | Path) -> moderngl.Texture | None:
        """Reload a texture from disk (for hot reload)."""
        self.unload(path)
        return self.load(path)

    def clear(self) -> None:
        """Unload all textures."""
        for texture in self._textures.values():
            texture.release()
        self._textures.clear()
        self._regions.clear()


class TextureAtlas:
    """
    A texture atlas (sprite sheet) with named regions.

    Supports:
    - Grid-based layouts (uniform tile sizes)
    - JSON metadata for named sprites
    - Animation frame sequences
    """

    def __init__(
        self,
        texture: moderngl.Texture,
        tile_width: int,
        tile_height: int,
    ):
        self.texture = texture
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.texture_width = texture.size[0]
        self.texture_height = texture.size[1]

        self._regions: dict[str, TextureRegion] = {}
        self._animations: dict[str, list[TextureRegion]] = {}

        # Calculate grid dimensions
        self.cols = self.texture_width // tile_width
        self.rows = self.texture_height // tile_height

    def get_region(self, col: int, row: int) -> TextureRegion:
        """
        Get a texture region by grid position.

        Args:
            col: Column index (0-based)
            row: Row index (0-based)

        Returns:
            TextureRegion for that tile
        """
        u0 = (col * self.tile_width) / self.texture_width
        v0 = (row * self.tile_height) / self.texture_height
        u1 = ((col + 1) * self.tile_width) / self.texture_width
        v1 = ((row + 1) * self.tile_height) / self.texture_height

        return TextureRegion(
            texture=self.texture,
            u0=u0, v0=v0, u1=u1, v1=v1,
            width=self.tile_width,
            height=self.tile_height,
        )

    def get_region_by_index(self, index: int) -> TextureRegion:
        """
        Get a texture region by linear index.

        Args:
            index: Linear tile index

        Returns:
            TextureRegion for that tile
        """
        col = index % self.cols
        row = index // self.cols
        return self.get_region(col, row)

    def get_region_by_name(self, name: str) -> TextureRegion:
        """Get a named texture region."""
        if name not in self._regions:
            raise KeyError(f"Region not found: {name}")
        return self._regions[name]

    def define_region(
        self,
        name: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> TextureRegion:
        """
        Define a named region by pixel coordinates.

        Args:
            name: Region name
            x: Left edge (pixels)
            y: Top edge (pixels)
            width: Width (pixels)
            height: Height (pixels)

        Returns:
            The defined region
        """
        u0 = x / self.texture_width
        v0 = y / self.texture_height
        u1 = (x + width) / self.texture_width
        v1 = (y + height) / self.texture_height

        region = TextureRegion(
            texture=self.texture,
            u0=u0, v0=v0, u1=u1, v1=v1,
            width=width, height=height,
        )
        self._regions[name] = region
        return region

    def define_animation(
        self,
        name: str,
        frames: list[tuple[int, int]] | list[int],
    ) -> list[TextureRegion]:
        """
        Define an animation sequence.

        Args:
            name: Animation name
            frames: List of (col, row) tuples or linear indices

        Returns:
            List of regions for the animation
        """
        regions = []
        for frame in frames:
            if isinstance(frame, int):
                regions.append(self.get_region_by_index(frame))
            else:
                regions.append(self.get_region(frame[0], frame[1]))

        self._animations[name] = regions
        return regions

    def get_animation(self, name: str) -> list[TextureRegion]:
        """Get animation frames by name."""
        if name not in self._animations:
            raise KeyError(f"Animation not found: {name}")
        return self._animations[name]

    @classmethod
    def from_json(
        cls,
        texture: moderngl.Texture,
        json_path: str | Path,
    ) -> TextureAtlas:
        """
        Load atlas definition from JSON file.

        Expected format:
        {
            "tile_width": 16,
            "tile_height": 16,
            "regions": {
                "player_idle": {"x": 0, "y": 0, "w": 16, "h": 16},
                ...
            },
            "animations": {
                "player_walk": [[0, 0], [1, 0], [2, 0], [3, 0]],
                ...
            }
        }
        """
        with open(json_path) as f:
            data = json.load(f)

        atlas = cls(
            texture=texture,
            tile_width=data.get("tile_width", 16),
            tile_height=data.get("tile_height", 16),
        )

        # Load regions
        for name, region_data in data.get("regions", {}).items():
            atlas.define_region(
                name,
                region_data["x"],
                region_data["y"],
                region_data["w"],
                region_data["h"],
            )

        # Load animations
        for name, frames in data.get("animations", {}).items():
            atlas.define_animation(name, frames)

        return atlas
