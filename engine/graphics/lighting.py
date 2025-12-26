"""
Dynamic lighting system.

Provides point lights, ambient lighting, and day/night cycle support.
Lighting is applied through shaders in SpriteBatch and TilemapRenderer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
import math

if TYPE_CHECKING:
    from engine.graphics.batch import SpriteBatch
    from engine.graphics.tilemap import TilemapRenderer


@dataclass
class PointLight:
    """
    A point light source.

    Attributes:
        x, y: World position
        radius: Light radius in pixels
        color: RGB color (0-1)
        intensity: Light intensity multiplier
        flicker: Optional flicker effect (0-1)
        flicker_speed: Flicker frequency
    """
    x: float
    y: float
    radius: float = 150.0
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    flicker: float = 0.0  # 0 = no flicker
    flicker_speed: float = 10.0
    enabled: bool = True

    # Runtime state
    _flicker_phase: float = 0.0
    _current_intensity: float = 1.0

    def update(self, dt: float) -> None:
        """Update light state (for flickering)."""
        if self.flicker > 0:
            self._flicker_phase += dt * self.flicker_speed
            flicker_value = math.sin(self._flicker_phase) * 0.5 + 0.5
            flicker_value += math.sin(self._flicker_phase * 2.3) * 0.25
            flicker_value = max(0, min(1, flicker_value))
            self._current_intensity = self.intensity * (1 - self.flicker * (1 - flicker_value))
        else:
            self._current_intensity = self.intensity

    def get_data(self) -> tuple[float, float, float, tuple[float, float, float], float]:
        """Get light data for shader (x, y, radius, color, intensity)."""
        return (self.x, self.y, self.radius, self.color, self._current_intensity)


@dataclass
class AmbientLight:
    """
    Global ambient lighting.

    Used for day/night cycles and overall scene mood.
    """
    color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    intensity: float = 0.3

    def get_color(self) -> tuple[float, float, float]:
        """Get ambient color multiplied by intensity."""
        return (
            self.color[0] * self.intensity,
            self.color[1] * self.intensity,
            self.color[2] * self.intensity,
        )


class DayNightCycle:
    """
    Simple day/night cycle controller.

    Interpolates ambient light between time-of-day presets.
    """

    # Default time presets: (hour, ambient_color, ambient_intensity)
    DEFAULT_PRESETS = [
        (0, (0.1, 0.1, 0.2), 0.15),    # Midnight
        (5, (0.2, 0.15, 0.3), 0.2),    # Pre-dawn
        (6, (0.8, 0.5, 0.4), 0.5),     # Sunrise
        (8, (1.0, 0.95, 0.9), 0.8),    # Morning
        (12, (1.0, 1.0, 1.0), 1.0),    # Noon
        (17, (1.0, 0.9, 0.8), 0.9),    # Afternoon
        (19, (0.9, 0.5, 0.3), 0.6),    # Sunset
        (21, (0.2, 0.2, 0.4), 0.25),   # Dusk
        (24, (0.1, 0.1, 0.2), 0.15),   # Midnight (wrap)
    ]

    def __init__(self):
        self.presets = list(self.DEFAULT_PRESETS)
        self.current_hour = 12.0  # 0-24
        self.time_scale = 1.0  # 1.0 = real-time equivalent

        self.ambient = AmbientLight()
        self._update_ambient()

    def set_time(self, hour: float) -> None:
        """Set current time (0-24)."""
        self.current_hour = hour % 24
        self._update_ambient()

    def advance_time(self, dt: float, hours_per_second: float = 0.1) -> None:
        """
        Advance time.

        Args:
            dt: Delta time in seconds
            hours_per_second: How many game hours per real second
        """
        self.current_hour = (self.current_hour + dt * hours_per_second * self.time_scale) % 24
        self._update_ambient()

    def _update_ambient(self) -> None:
        """Interpolate ambient light based on current time."""
        hour = self.current_hour

        # Find surrounding presets
        prev_preset = self.presets[-1]
        next_preset = self.presets[0]

        for i, preset in enumerate(self.presets):
            if preset[0] > hour:
                prev_preset = self.presets[i - 1]
                next_preset = preset
                break

        # Calculate interpolation factor
        prev_hour = prev_preset[0]
        next_hour = next_preset[0]

        if next_hour <= prev_hour:
            next_hour += 24
        if hour < prev_hour:
            hour += 24

        t = (hour - prev_hour) / (next_hour - prev_hour) if next_hour != prev_hour else 0

        # Smooth interpolation
        t = t * t * (3 - 2 * t)  # Smoothstep

        # Interpolate color and intensity
        prev_color = prev_preset[1]
        next_color = next_preset[1]
        prev_intensity = prev_preset[2]
        next_intensity = next_preset[2]

        self.ambient.color = (
            prev_color[0] + (next_color[0] - prev_color[0]) * t,
            prev_color[1] + (next_color[1] - prev_color[1]) * t,
            prev_color[2] + (next_color[2] - prev_color[2]) * t,
        )
        self.ambient.intensity = prev_intensity + (next_intensity - prev_intensity) * t


class LightingSystem:
    """
    Manages all lighting in a scene.

    Collects lights, updates them, and provides data to renderers.
    """

    MAX_LIGHTS = 16

    def __init__(self):
        self.enabled = True
        self.ambient = AmbientLight()
        self.lights: list[PointLight] = []
        self.day_night: DayNightCycle | None = None

    def add_light(self, light: PointLight) -> PointLight:
        """Add a point light."""
        self.lights.append(light)
        return light

    def remove_light(self, light: PointLight) -> None:
        """Remove a point light."""
        if light in self.lights:
            self.lights.remove(light)

    def create_light(
        self,
        x: float,
        y: float,
        radius: float = 150.0,
        color: tuple[float, float, float] = (1.0, 1.0, 1.0),
        intensity: float = 1.0,
        flicker: float = 0.0,
    ) -> PointLight:
        """Create and add a new light."""
        light = PointLight(
            x=x, y=y,
            radius=radius,
            color=color,
            intensity=intensity,
            flicker=flicker,
        )
        return self.add_light(light)

    def enable_day_night(self, start_hour: float = 12.0) -> DayNightCycle:
        """Enable day/night cycle."""
        self.day_night = DayNightCycle()
        self.day_night.set_time(start_hour)
        return self.day_night

    def update(self, dt: float) -> None:
        """Update all lights and day/night cycle."""
        # Update day/night cycle
        if self.day_night:
            self.day_night.advance_time(dt)
            self.ambient = self.day_night.ambient

        # Update individual lights
        for light in self.lights:
            light.update(dt)

    def get_visible_lights(
        self,
        view_x: float,
        view_y: float,
        view_width: float,
        view_height: float,
    ) -> list[tuple[float, float, float, tuple[float, float, float], float]]:
        """
        Get light data for visible lights.

        Args:
            view_x, view_y: View top-left
            view_width, view_height: View dimensions

        Returns:
            List of (x, y, radius, color, intensity) tuples
        """
        result = []

        for light in self.lights:
            if not light.enabled:
                continue

            # Check if light is visible (with radius margin)
            if (light.x + light.radius < view_x or
                light.x - light.radius > view_x + view_width or
                light.y + light.radius < view_y or
                light.y - light.radius > view_y + view_height):
                continue

            result.append(light.get_data())

            if len(result) >= self.MAX_LIGHTS:
                break

        return result

    def apply_to_batch(
        self,
        batch: SpriteBatch,
        view_x: float,
        view_y: float,
        view_width: float,
        view_height: float,
    ) -> None:
        """Apply lighting to a sprite batch."""
        batch.set_lighting(self.enabled, self.ambient.get_color())
        batch.clear_lights()

        if self.enabled:
            for light_data in self.get_visible_lights(view_x, view_y, view_width, view_height):
                batch.add_light(*light_data)

    def apply_to_tilemap(
        self,
        renderer: TilemapRenderer,
        view_x: float,
        view_y: float,
        view_width: float,
        view_height: float,
    ) -> None:
        """Apply lighting to a tilemap renderer."""
        renderer.set_lighting(self.enabled, self.ambient.get_color())
        lights = self.get_visible_lights(view_x, view_y, view_width, view_height)
        renderer.set_lights(lights)

    def clear(self) -> None:
        """Remove all lights."""
        self.lights.clear()
