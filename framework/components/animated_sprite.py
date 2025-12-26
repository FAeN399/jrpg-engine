"""
AnimatedSprite component - Sprite with animation support.

This component holds all animation-related data for an entity.
The AnimationSystem processes entities with this component.
"""

from __future__ import annotations

from typing import Optional, Any, TYPE_CHECKING
from enum import Enum, auto

from engine.core.component import Component

if TYPE_CHECKING:
    from engine.graphics.animation import AnimationController, AnimationSet


class SpriteLayer(Enum):
    """Rendering layers for sprites."""
    BACKGROUND = auto()  # Behind everything
    FLOOR = auto()       # Floor decorations
    SHADOW = auto()      # Character shadows
    ENTITY = auto()      # Characters, NPCs, objects
    EFFECT = auto()      # Visual effects
    OVERLAY = auto()     # Above everything


class AnimatedSprite(Component):
    """
    Component for entities with animated sprites.

    DATA ONLY - all animation logic lives in AnimationSystem.

    Attributes:
        animation_set_name: Name of registered AnimationSet to use
        current_clip: Name of currently playing animation clip
        playing: Whether animation is currently playing
        speed: Playback speed multiplier
        current_time: Current time in animation (seconds)
        current_frame_index: Index of current frame
        flip_x: Mirror sprite horizontally
        flip_y: Mirror sprite vertically
        visible: Whether sprite should be rendered
        layer: Rendering layer
        z_offset: Additional z-offset for sorting
        tint: Color tint (r, g, b, a) values 0-255
        alpha: Transparency (0.0 = invisible, 1.0 = opaque)
        texture_region: Current texture region name (set by system)
        offset_x: Frame offset X (set by system from animation data)
        offset_y: Frame offset Y (set by system from animation data)
    """
    # Animation source
    animation_set_name: str = ""

    # Playback state (managed by AnimationSystem)
    current_clip: str = "idle"
    playing: bool = True
    speed: float = 1.0
    current_time: float = 0.0
    current_frame_index: int = 0
    completed: bool = False

    # Sprite rendering properties
    flip_x: bool = False
    flip_y: bool = False
    visible: bool = True
    layer: SpriteLayer = SpriteLayer.ENTITY
    z_offset: float = 0.0

    # Visual modifiers
    tint_r: int = 255
    tint_g: int = 255
    tint_b: int = 255
    tint_a: int = 255
    alpha: float = 1.0

    # Frame data (set by AnimationSystem each frame)
    texture_region: str = ""
    offset_x: float = 0.0
    offset_y: float = 0.0

    # Atlas reference for rendering
    atlas_name: str = ""
    frame_width: int = 32
    frame_height: int = 32

    @property
    def tint(self) -> tuple[int, int, int, int]:
        """Get tint as tuple."""
        return (self.tint_r, self.tint_g, self.tint_b, self.tint_a)

    @tint.setter
    def tint(self, value: tuple[int, int, int, int]) -> None:
        """Set tint from tuple."""
        self.tint_r, self.tint_g, self.tint_b, self.tint_a = value

    def set_tint_rgb(self, r: int, g: int, b: int) -> None:
        """Set RGB tint, keeping alpha."""
        self.tint_r = r
        self.tint_g = g
        self.tint_b = b

    def reset_tint(self) -> None:
        """Reset to default white tint."""
        self.tint_r = 255
        self.tint_g = 255
        self.tint_b = 255
        self.tint_a = 255


class Sprite(Component):
    """
    Simple static sprite component (no animation).

    For entities that just display a single image.
    """
    texture_name: str = ""
    region_name: str = ""  # If using atlas

    # Rendering
    flip_x: bool = False
    flip_y: bool = False
    visible: bool = True
    layer: SpriteLayer = SpriteLayer.ENTITY
    z_offset: float = 0.0

    # Visual
    tint_r: int = 255
    tint_g: int = 255
    tint_b: int = 255
    tint_a: int = 255
    alpha: float = 1.0

    # Size (0 = use texture size)
    width: float = 0.0
    height: float = 0.0

    # Origin (for rotation/scaling)
    origin_x: float = 0.5  # 0.5 = center
    origin_y: float = 0.5

    @property
    def tint(self) -> tuple[int, int, int, int]:
        """Get tint as tuple."""
        return (self.tint_r, self.tint_g, self.tint_b, self.tint_a)

    @tint.setter
    def tint(self, value: tuple[int, int, int, int]) -> None:
        """Set tint from tuple."""
        self.tint_r, self.tint_g, self.tint_b, self.tint_a = value


class SpriteFlash(Component):
    """
    Temporary flash effect for sprites.

    Used for damage flashes, pickups, etc.
    AnimationSystem removes this after duration.
    """
    flash_r: int = 255
    flash_g: int = 255
    flash_b: int = 255
    duration: float = 0.1
    elapsed: float = 0.0
    original_tint_r: int = 255
    original_tint_g: int = 255
    original_tint_b: int = 255

    @classmethod
    def damage_flash(cls) -> 'SpriteFlash':
        """Create red damage flash."""
        return cls(flash_r=255, flash_g=100, flash_b=100, duration=0.15)

    @classmethod
    def heal_flash(cls) -> 'SpriteFlash':
        """Create green heal flash."""
        return cls(flash_r=100, flash_g=255, flash_b=100, duration=0.2)

    @classmethod
    def pickup_flash(cls) -> 'SpriteFlash':
        """Create yellow pickup flash."""
        return cls(flash_r=255, flash_g=255, flash_b=150, duration=0.1)
