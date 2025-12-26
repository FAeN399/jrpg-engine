"""
Camera system with smooth follow, shake, and zoom.

Handles converting between world and screen coordinates.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


@dataclass
class CameraBounds:
    """Rectangular bounds for camera movement."""
    left: float = float('-inf')
    top: float = float('-inf')
    right: float = float('inf')
    bottom: float = float('inf')

    def clamp(self, x: float, y: float, view_width: float, view_height: float) -> tuple[float, float]:
        """Clamp camera position to bounds."""
        # Camera position is top-left of view
        min_x = self.left
        min_y = self.top
        max_x = max(self.left, self.right - view_width)
        max_y = max(self.top, self.bottom - view_height)

        return (
            max(min_x, min(x, max_x)),
            max(min_y, min(y, max_y)),
        )


@dataclass
class CameraShake:
    """Camera shake effect data."""
    intensity: float = 0.0
    duration: float = 0.0
    elapsed: float = 0.0
    frequency: float = 30.0  # Shakes per second
    decay: float = 0.9  # Intensity decay per shake
    offset_x: float = 0.0
    offset_y: float = 0.0


class Camera:
    """
    2D camera with follow, bounds, shake, and zoom.

    Usage:
        camera = Camera(1280, 720)
        camera.follow(player_x, player_y, dt)
        camera.apply(sprite_batch)

        # Screen shake
        camera.shake(10, 0.5)  # intensity, duration
    """

    def __init__(
        self,
        view_width: float,
        view_height: float,
        zoom: float = 1.0,
    ):
        # View dimensions
        self.view_width = view_width
        self.view_height = view_height

        # Position (top-left of view in world coordinates)
        self._x = 0.0
        self._y = 0.0

        # Target for smooth follow
        self._target_x = 0.0
        self._target_y = 0.0

        # Zoom
        self._zoom = zoom
        self._target_zoom = zoom

        # Bounds
        self.bounds: CameraBounds | None = None

        # Shake
        self._shake = CameraShake()

        # Follow settings
        self.follow_lerp = 5.0  # Higher = faster follow
        self.follow_deadzone = 0.0  # Pixels before camera moves
        self.follow_offset_x = 0.0  # Look-ahead offset
        self.follow_offset_y = 0.0

        # Zoom settings
        self.zoom_lerp = 5.0
        self.min_zoom = 0.25
        self.max_zoom = 4.0

    @property
    def x(self) -> float:
        """Camera X position (with shake)."""
        return self._x + self._shake.offset_x

    @property
    def y(self) -> float:
        """Camera Y position (with shake)."""
        return self._y + self._shake.offset_y

    @property
    def zoom(self) -> float:
        """Current zoom level."""
        return self._zoom

    @zoom.setter
    def zoom(self, value: float) -> None:
        """Set zoom level."""
        self._zoom = max(self.min_zoom, min(value, self.max_zoom))
        self._target_zoom = self._zoom

    @property
    def center_x(self) -> float:
        """X coordinate of view center."""
        return self._x + self.view_width / (2 * self._zoom)

    @property
    def center_y(self) -> float:
        """Y coordinate of view center."""
        return self._y + self.view_height / (2 * self._zoom)

    @property
    def scaled_width(self) -> float:
        """View width adjusted for zoom."""
        return self.view_width / self._zoom

    @property
    def scaled_height(self) -> float:
        """View height adjusted for zoom."""
        return self.view_height / self._zoom

    def set_position(self, x: float, y: float) -> None:
        """Set camera position immediately (no lerp)."""
        self._x = x
        self._y = y
        self._target_x = x
        self._target_y = y
        self._apply_bounds()

    def set_center(self, x: float, y: float) -> None:
        """Center camera on a point immediately."""
        self.set_position(
            x - self.scaled_width / 2,
            y - self.scaled_height / 2,
        )

    def look_at(self, x: float, y: float) -> None:
        """Set target to center on a point (will lerp)."""
        self._target_x = x - self.scaled_width / 2 + self.follow_offset_x
        self._target_y = y - self.scaled_height / 2 + self.follow_offset_y

    def follow(self, x: float, y: float, dt: float) -> None:
        """
        Smoothly follow a target position.

        Args:
            x, y: Target world position to follow
            dt: Delta time in seconds
        """
        # Calculate target camera position (centered on target)
        target_x = x - self.scaled_width / 2 + self.follow_offset_x
        target_y = y - self.scaled_height / 2 + self.follow_offset_y

        # Apply deadzone
        if self.follow_deadzone > 0:
            dx = target_x - self._x
            dy = target_y - self._y
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < self.follow_deadzone:
                return

        self._target_x = target_x
        self._target_y = target_y

    def update(self, dt: float) -> None:
        """
        Update camera state.

        Call this each frame after follow().
        """
        # Smooth position follow
        if self.follow_lerp > 0:
            t = 1 - math.exp(-self.follow_lerp * dt)
            self._x += (self._target_x - self._x) * t
            self._y += (self._target_y - self._y) * t
        else:
            self._x = self._target_x
            self._y = self._target_y

        # Smooth zoom
        if self.zoom_lerp > 0:
            t = 1 - math.exp(-self.zoom_lerp * dt)
            self._zoom += (self._target_zoom - self._zoom) * t
        else:
            self._zoom = self._target_zoom

        # Apply bounds
        self._apply_bounds()

        # Update shake
        self._update_shake(dt)

    def _apply_bounds(self) -> None:
        """Apply camera bounds."""
        if self.bounds:
            self._x, self._y = self.bounds.clamp(
                self._x, self._y,
                self.scaled_width, self.scaled_height,
            )

    def _update_shake(self, dt: float) -> None:
        """Update shake effect."""
        if self._shake.duration <= 0:
            self._shake.offset_x = 0
            self._shake.offset_y = 0
            return

        self._shake.elapsed += dt

        if self._shake.elapsed >= self._shake.duration:
            self._shake.duration = 0
            self._shake.offset_x = 0
            self._shake.offset_y = 0
            return

        # Calculate shake offset
        progress = self._shake.elapsed / self._shake.duration
        current_intensity = self._shake.intensity * (1 - progress)

        # Random offset based on frequency
        phase = self._shake.elapsed * self._shake.frequency
        self._shake.offset_x = math.sin(phase * 1.1) * current_intensity
        self._shake.offset_y = math.cos(phase * 1.3) * current_intensity

    def shake(
        self,
        intensity: float,
        duration: float,
        frequency: float = 30.0,
    ) -> None:
        """
        Start a camera shake effect.

        Args:
            intensity: Maximum pixel offset
            duration: Duration in seconds
            frequency: Shake frequency
        """
        self._shake.intensity = intensity
        self._shake.duration = duration
        self._shake.elapsed = 0
        self._shake.frequency = frequency

    def zoom_to(self, zoom: float, instant: bool = False) -> None:
        """
        Set target zoom level.

        Args:
            zoom: Target zoom level
            instant: If True, apply immediately
        """
        self._target_zoom = max(self.min_zoom, min(zoom, self.max_zoom))
        if instant:
            self._zoom = self._target_zoom

    def zoom_in(self, amount: float = 0.1) -> None:
        """Zoom in by a factor."""
        self.zoom_to(self._target_zoom + amount)

    def zoom_out(self, amount: float = 0.1) -> None:
        """Zoom out by a factor."""
        self.zoom_to(self._target_zoom - amount)

    # Coordinate conversion

    def world_to_screen(self, world_x: float, world_y: float) -> tuple[float, float]:
        """Convert world coordinates to screen coordinates."""
        return (
            (world_x - self.x) * self._zoom,
            (world_y - self.y) * self._zoom,
        )

    def screen_to_world(self, screen_x: float, screen_y: float) -> tuple[float, float]:
        """Convert screen coordinates to world coordinates."""
        return (
            screen_x / self._zoom + self.x,
            screen_y / self._zoom + self.y,
        )

    def is_visible(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        margin: float = 0,
    ) -> bool:
        """
        Check if a rectangle is visible in the camera view.

        Args:
            x, y: Top-left of rectangle
            width, height: Size of rectangle
            margin: Extra margin around view

        Returns:
            True if any part of the rectangle is visible
        """
        view_left = self.x - margin
        view_top = self.y - margin
        view_right = self.x + self.scaled_width + margin
        view_bottom = self.y + self.scaled_height + margin

        return not (
            x + width < view_left or
            x > view_right or
            y + height < view_top or
            y > view_bottom
        )

    def apply(self, batch) -> None:
        """
        Apply camera to a sprite batch.

        Args:
            batch: SpriteBatch to configure
        """
        batch.set_camera(self.x, self.y)
        batch.set_projection(self.view_width / self._zoom, self.view_height / self._zoom)
