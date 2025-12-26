"""
Transform components - position, rotation, scale, velocity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from engine.core.component import Component, register_component


class Direction(Enum):
    """Cardinal and ordinal directions."""
    NONE = auto()
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    UP_LEFT = auto()
    UP_RIGHT = auto()
    DOWN_LEFT = auto()
    DOWN_RIGHT = auto()

    @property
    def vector(self) -> tuple[float, float]:
        """Get normalized direction vector."""
        vectors = {
            Direction.NONE: (0.0, 0.0),
            Direction.UP: (0.0, -1.0),
            Direction.DOWN: (0.0, 1.0),
            Direction.LEFT: (-1.0, 0.0),
            Direction.RIGHT: (1.0, 0.0),
            Direction.UP_LEFT: (-0.707, -0.707),
            Direction.UP_RIGHT: (0.707, -0.707),
            Direction.DOWN_LEFT: (-0.707, 0.707),
            Direction.DOWN_RIGHT: (0.707, 0.707),
        }
        return vectors.get(self, (0.0, 0.0))

    @staticmethod
    def from_vector(dx: float, dy: float) -> Direction:
        """Get direction from movement vector."""
        if abs(dx) < 0.01 and abs(dy) < 0.01:
            return Direction.NONE

        # Determine primary direction
        if abs(dx) > abs(dy) * 2:
            return Direction.RIGHT if dx > 0 else Direction.LEFT
        elif abs(dy) > abs(dx) * 2:
            return Direction.DOWN if dy > 0 else Direction.UP
        else:
            # Diagonal
            if dx > 0:
                return Direction.DOWN_RIGHT if dy > 0 else Direction.UP_RIGHT
            else:
                return Direction.DOWN_LEFT if dy > 0 else Direction.UP_LEFT


@register_component
class Transform(Component):
    """
    Position and orientation in world space.

    Attributes:
        x: X position in pixels
        y: Y position in pixels
        z: Z-order for rendering (higher = on top)
        rotation: Rotation in degrees
        scale_x: Horizontal scale factor
        scale_y: Vertical scale factor
        facing: Current facing direction
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    facing: Direction = Direction.DOWN

    @property
    def position(self) -> tuple[float, float]:
        """Get position as tuple."""
        return (self.x, self.y)

    @position.setter
    def position(self, value: tuple[float, float]) -> None:
        """Set position from tuple."""
        self.x, self.y = value

    @property
    def tile_position(self) -> tuple[int, int]:
        """Get tile position (assuming 16x16 tiles)."""
        return (int(self.x // 16), int(self.y // 16))

    def move(self, dx: float, dy: float) -> None:
        """Move by delta."""
        self.x += dx
        self.y += dy

    def move_to(self, x: float, y: float) -> None:
        """Move to absolute position."""
        self.x = x
        self.y = y

    def distance_to(self, other: Transform) -> float:
        """Calculate distance to another transform."""
        dx = other.x - self.x
        dy = other.y - self.y
        return (dx * dx + dy * dy) ** 0.5


@register_component
class Velocity(Component):
    """
    Movement velocity.

    Attributes:
        vx: Horizontal velocity (pixels/second)
        vy: Vertical velocity (pixels/second)
        max_speed: Maximum speed
        friction: Friction coefficient (0-1, applied per second)
    """
    vx: float = 0.0
    vy: float = 0.0
    max_speed: float = 200.0
    friction: float = 0.0

    @property
    def speed(self) -> float:
        """Get current speed magnitude."""
        return (self.vx * self.vx + self.vy * self.vy) ** 0.5

    @property
    def direction(self) -> Direction:
        """Get direction from velocity."""
        return Direction.from_vector(self.vx, self.vy)

    def apply_friction(self, dt: float) -> None:
        """Apply friction to velocity."""
        if self.friction > 0:
            factor = max(0, 1 - self.friction * dt)
            self.vx *= factor
            self.vy *= factor

    def clamp_speed(self) -> None:
        """Clamp velocity to max speed."""
        speed = self.speed
        if speed > self.max_speed:
            factor = self.max_speed / speed
            self.vx *= factor
            self.vy *= factor

    def set_velocity(self, direction: Direction, speed: float) -> None:
        """Set velocity from direction and speed."""
        vec = direction.vector
        self.vx = vec[0] * speed
        self.vy = vec[1] * speed
