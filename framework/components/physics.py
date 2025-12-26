"""
Physics components - collision shapes and physics properties.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from engine.core.component import Component


class ColliderType(Enum):
    """Types of collision shapes."""
    NONE = auto()      # No collision
    AABB = auto()      # Axis-aligned bounding box
    CIRCLE = auto()    # Circle collider
    TILE = auto()      # Tile-based collision


class CollisionLayer(Enum):
    """Collision layers for filtering."""
    NONE = 0
    PLAYER = 1 << 0
    ENEMY = 1 << 1
    NPC = 1 << 2
    PROJECTILE = 1 << 3
    TRIGGER = 1 << 4
    WALL = 1 << 5
    INTERACTABLE = 1 << 6

    # Common masks
    ALL = 0xFFFFFFFF
    CHARACTERS = PLAYER | ENEMY | NPC
    SOLID = PLAYER | ENEMY | NPC | WALL


@dataclass
class Collider(Component):
    """
    Collision shape and layer information.

    Attributes:
        collider_type: Shape type (AABB, Circle, etc.)
        width: Width for AABB
        height: Height for AABB
        radius: Radius for circle
        offset_x: Offset from transform X
        offset_y: Offset from transform Y
        layer: What layer this collider is on
        mask: What layers this collider interacts with
        is_trigger: If True, detects overlap but doesn't block
        is_static: If True, doesn't move (optimization)
    """
    collider_type: ColliderType = ColliderType.AABB
    width: float = 16.0
    height: float = 16.0
    radius: float = 8.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    layer: int = CollisionLayer.NONE.value
    mask: int = CollisionLayer.ALL.value
    is_trigger: bool = False
    is_static: bool = False

    def get_bounds(self, x: float, y: float) -> tuple[float, float, float, float]:
        """
        Get AABB bounds at position.

        Returns:
            (left, top, right, bottom)
        """
        cx = x + self.offset_x
        cy = y + self.offset_y

        if self.collider_type == ColliderType.CIRCLE:
            return (
                cx - self.radius,
                cy - self.radius,
                cx + self.radius,
                cy + self.radius,
            )
        else:
            half_w = self.width / 2
            half_h = self.height / 2
            return (
                cx - half_w,
                cy - half_h,
                cx + half_w,
                cy + half_h,
            )

    def overlaps_layer(self, other_layer: int) -> bool:
        """Check if this collider's mask includes the other layer."""
        return (self.mask & other_layer) != 0

    def set_layer(self, layer: CollisionLayer) -> None:
        """Set collision layer."""
        self.layer = layer.value

    def add_to_mask(self, layer: CollisionLayer) -> None:
        """Add a layer to the collision mask."""
        self.mask |= layer.value

    def remove_from_mask(self, layer: CollisionLayer) -> None:
        """Remove a layer from the collision mask."""
        self.mask &= ~layer.value


@dataclass
class RigidBody(Component):
    """
    Physics body properties.

    Attributes:
        mass: Mass in arbitrary units
        gravity_scale: Multiplier for gravity
        is_kinematic: If True, not affected by physics forces
        bounce: Bounciness (0-1)
        drag: Air resistance
    """
    mass: float = 1.0
    gravity_scale: float = 0.0  # Top-down games typically don't use gravity
    is_kinematic: bool = False
    bounce: float = 0.0
    drag: float = 0.0


@dataclass
class TileCollision(Component):
    """
    Tile-based collision for maps.

    Attributes:
        solid_tiles: Set of tile IDs that are solid
        collision_map: 2D array of collision flags (optional)
        tile_width: Width of tiles in pixels
        tile_height: Height of tiles in pixels
    """
    solid_tiles: set[int] = field(default_factory=set)
    tile_width: int = 16
    tile_height: int = 16
    # collision_map is stored separately in the map data
