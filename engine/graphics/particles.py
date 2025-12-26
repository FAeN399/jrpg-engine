"""
GPU-accelerated particle system.

Supports various emitter types and particle behaviors.
Renders particles using instanced drawing for performance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable
import math
import random
import struct

import moderngl
import numpy as np

if TYPE_CHECKING:
    from engine.graphics.texture import TextureRegion


class EmitterShape(Enum):
    """Particle emitter shapes."""
    POINT = auto()
    LINE = auto()
    CIRCLE = auto()
    RECTANGLE = auto()


class BlendMode(Enum):
    """Particle blend modes."""
    NORMAL = auto()
    ADDITIVE = auto()
    MULTIPLY = auto()


@dataclass
class ParticleConfig:
    """
    Configuration for a particle type.

    All ranges are (min, max) tuples for randomization.
    """
    # Lifetime
    lifetime: tuple[float, float] = (1.0, 2.0)

    # Initial velocity
    speed: tuple[float, float] = (50.0, 100.0)
    direction: tuple[float, float] = (0.0, 360.0)  # Degrees

    # Physics
    gravity_x: float = 0.0
    gravity_y: float = 0.0
    drag: float = 0.0  # 0-1, velocity reduction per second

    # Size
    start_size: tuple[float, float] = (8.0, 16.0)
    end_size: tuple[float, float] = (4.0, 8.0)

    # Color (RGBA, 0-1)
    start_color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    end_color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 0.0)

    # Rotation
    start_rotation: tuple[float, float] = (0.0, 0.0)
    rotation_speed: tuple[float, float] = (0.0, 0.0)  # Degrees per second

    # Texture (if None, uses white square)
    texture_region: TextureRegion | None = None

    # Blend mode
    blend_mode: BlendMode = BlendMode.NORMAL


@dataclass
class Particle:
    """Single particle instance."""
    x: float
    y: float
    vx: float
    vy: float
    lifetime: float
    max_lifetime: float
    size: float
    start_size: float
    end_size: float
    rotation: float
    rotation_speed: float
    start_color: tuple[float, float, float, float]
    end_color: tuple[float, float, float, float]
    alive: bool = True


# Particle vertex shader
PARTICLE_VERTEX_SHADER = """
#version 330 core

in vec2 in_position;
in vec2 in_texcoord;
in vec4 in_color;
in float in_size;
in float in_rotation;

out vec2 v_texcoord;
out vec4 v_color;

uniform mat4 u_projection;
uniform vec2 u_camera;

void main() {
    // Apply rotation to local position
    float cos_r = cos(in_rotation);
    float sin_r = sin(in_rotation);

    vec2 local = in_texcoord - 0.5;  // Center
    vec2 rotated = vec2(
        local.x * cos_r - local.y * sin_r,
        local.x * sin_r + local.y * cos_r
    );
    vec2 scaled = rotated * in_size;

    vec2 world_pos = in_position + scaled;
    vec2 view_pos = world_pos - u_camera;

    gl_Position = u_projection * vec4(view_pos, 0.0, 1.0);
    v_texcoord = in_texcoord;
    v_color = in_color;
}
"""

PARTICLE_FRAGMENT_SHADER = """
#version 330 core

in vec2 v_texcoord;
in vec4 v_color;

out vec4 fragColor;

uniform sampler2D u_texture;
uniform bool u_use_texture;

void main() {
    vec4 color;

    if (u_use_texture) {
        color = texture(u_texture, v_texcoord) * v_color;
    } else {
        // Simple circle falloff
        vec2 center = v_texcoord - 0.5;
        float dist = length(center) * 2.0;
        float alpha = 1.0 - smoothstep(0.8, 1.0, dist);
        color = vec4(v_color.rgb, v_color.a * alpha);
    }

    if (color.a < 0.01) {
        discard;
    }

    fragColor = color;
}
"""


class ParticleEmitter:
    """
    Particle emitter that spawns and manages particles.

    Usage:
        emitter = ParticleEmitter(config)
        emitter.position = (100, 100)
        emitter.emit(10)  # Burst
        emitter.emit_rate = 50  # Continuous

        # In update loop:
        emitter.update(dt)

        # In render loop:
        particle_system.render(emitter)
    """

    def __init__(self, config: ParticleConfig, max_particles: int = 1000):
        self.config = config
        self.max_particles = max_particles

        # Emitter properties
        self.x = 0.0
        self.y = 0.0
        self.shape = EmitterShape.POINT
        self.shape_width = 0.0
        self.shape_height = 0.0
        self.emit_rate = 0.0  # Particles per second (0 = manual only)
        self.enabled = True

        # Particles
        self.particles: list[Particle] = []
        self._emit_accumulator = 0.0

    def emit(self, count: int = 1) -> None:
        """Emit particles immediately."""
        for _ in range(count):
            if len(self.particles) >= self.max_particles:
                # Recycle oldest particle
                self.particles.pop(0)

            particle = self._create_particle()
            self.particles.append(particle)

    def update(self, dt: float) -> None:
        """Update all particles."""
        if not self.enabled:
            return

        # Continuous emission
        if self.emit_rate > 0:
            self._emit_accumulator += dt * self.emit_rate
            while self._emit_accumulator >= 1.0:
                self.emit(1)
                self._emit_accumulator -= 1.0

        # Update particles
        gravity_x = self.config.gravity_x
        gravity_y = self.config.gravity_y
        drag = self.config.drag

        alive_particles = []
        for p in self.particles:
            if not p.alive:
                continue

            # Age
            p.lifetime -= dt
            if p.lifetime <= 0:
                p.alive = False
                continue

            # Physics
            p.vx += gravity_x * dt
            p.vy += gravity_y * dt

            if drag > 0:
                factor = 1.0 - drag * dt
                p.vx *= factor
                p.vy *= factor

            p.x += p.vx * dt
            p.y += p.vy * dt

            # Rotation
            p.rotation += p.rotation_speed * dt

            # Size interpolation
            t = 1.0 - (p.lifetime / p.max_lifetime)
            p.size = p.start_size + (p.end_size - p.start_size) * t

            alive_particles.append(p)

        self.particles = alive_particles

    def _create_particle(self) -> Particle:
        """Create a new particle with randomized properties."""
        cfg = self.config

        # Position based on emitter shape
        x, y = self._get_spawn_position()

        # Velocity
        speed = random.uniform(*cfg.speed)
        direction = math.radians(random.uniform(*cfg.direction))
        vx = math.cos(direction) * speed
        vy = math.sin(direction) * speed

        # Lifetime
        lifetime = random.uniform(*cfg.lifetime)

        # Size
        start_size = random.uniform(*cfg.start_size)
        end_size = random.uniform(*cfg.end_size)

        # Rotation
        rotation = math.radians(random.uniform(*cfg.start_rotation))
        rotation_speed = math.radians(random.uniform(*cfg.rotation_speed))

        return Particle(
            x=x, y=y,
            vx=vx, vy=vy,
            lifetime=lifetime,
            max_lifetime=lifetime,
            size=start_size,
            start_size=start_size,
            end_size=end_size,
            rotation=rotation,
            rotation_speed=rotation_speed,
            start_color=cfg.start_color,
            end_color=cfg.end_color,
        )

    def _get_spawn_position(self) -> tuple[float, float]:
        """Get spawn position based on emitter shape."""
        if self.shape == EmitterShape.POINT:
            return (self.x, self.y)

        elif self.shape == EmitterShape.LINE:
            t = random.random()
            return (
                self.x + t * self.shape_width,
                self.y,
            )

        elif self.shape == EmitterShape.CIRCLE:
            angle = random.random() * math.pi * 2
            radius = random.random() * self.shape_width
            return (
                self.x + math.cos(angle) * radius,
                self.y + math.sin(angle) * radius,
            )

        elif self.shape == EmitterShape.RECTANGLE:
            return (
                self.x + random.random() * self.shape_width,
                self.y + random.random() * self.shape_height,
            )

        return (self.x, self.y)

    def clear(self) -> None:
        """Remove all particles."""
        self.particles.clear()


class ParticleSystem:
    """
    Renders particle emitters efficiently.

    Batches particles for minimal draw calls.
    """

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx

        # Shader
        self.program = ctx.program(
            vertex_shader=PARTICLE_VERTEX_SHADER,
            fragment_shader=PARTICLE_FRAGMENT_SHADER,
        )

        # Dynamic vertex buffer
        self.max_particles = 10000
        buffer_size = self.max_particles * 6 * 10 * 4  # 6 verts, 10 floats, 4 bytes
        self.vbo = ctx.buffer(reserve=buffer_size, dynamic=True)

        self.vao = ctx.vertex_array(
            self.program,
            [(self.vbo, '2f 2f 4f 1f 1f', 'in_position', 'in_texcoord', 'in_color', 'in_size', 'in_rotation')],
        )

        # Projection
        self._projection = self._ortho_matrix(1280, 720)
        self._camera_x = 0.0
        self._camera_y = 0.0

    def set_projection(self, width: float, height: float) -> None:
        """Set projection matrix."""
        self._projection = self._ortho_matrix(width, height)

    def set_camera(self, x: float, y: float) -> None:
        """Set camera offset."""
        self._camera_x = x
        self._camera_y = y

    def render(self, *emitters: ParticleEmitter) -> None:
        """Render particle emitters."""
        vertices = []
        total_particles = 0

        for emitter in emitters:
            for p in emitter.particles:
                if not p.alive:
                    continue

                # Interpolate color
                t = 1.0 - (p.lifetime / p.max_lifetime)
                r = p.start_color[0] + (p.end_color[0] - p.start_color[0]) * t
                g = p.start_color[1] + (p.end_color[1] - p.start_color[1]) * t
                b = p.start_color[2] + (p.end_color[2] - p.start_color[2]) * t
                a = p.start_color[3] + (p.end_color[3] - p.start_color[3]) * t

                # Quad vertices (6 vertices)
                for uv in [(0, 0), (1, 0), (1, 1), (0, 0), (1, 1), (0, 1)]:
                    vertices.extend([
                        p.x, p.y,           # position
                        uv[0], uv[1],       # texcoord
                        r, g, b, a,         # color
                        p.size,             # size
                        p.rotation,         # rotation
                    ])

                total_particles += 1

        if total_particles == 0:
            return

        # Upload and render
        data = struct.pack(f'{len(vertices)}f', *vertices)
        self.vbo.orphan(len(data))
        self.vbo.write(data)

        self.program['u_projection'].write(self._projection.tobytes())
        self.program['u_camera'].value = (self._camera_x, self._camera_y)
        self.program['u_use_texture'].value = False

        # Enable additive blending for particles
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE

        self.vao.render(vertices=total_particles * 6)

        # Restore normal blending
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

    def _ortho_matrix(self, width: float, height: float) -> np.ndarray:
        """Create orthographic projection matrix."""
        return np.array([
            [2 / width, 0, 0, -1],
            [0, -2 / height, 0, 1],
            [0, 0, -1, 0],
            [0, 0, 0, 1],
        ], dtype='f4')


# Preset particle configurations
class ParticlePresets:
    """Common particle effect presets."""

    @staticmethod
    def fire() -> ParticleConfig:
        return ParticleConfig(
            lifetime=(0.5, 1.0),
            speed=(30.0, 60.0),
            direction=(250.0, 290.0),
            gravity_y=-50.0,
            start_size=(12.0, 20.0),
            end_size=(4.0, 8.0),
            start_color=(1.0, 0.6, 0.2, 1.0),
            end_color=(1.0, 0.2, 0.0, 0.0),
            blend_mode=BlendMode.ADDITIVE,
        )

    @staticmethod
    def smoke() -> ParticleConfig:
        return ParticleConfig(
            lifetime=(1.5, 3.0),
            speed=(10.0, 30.0),
            direction=(250.0, 290.0),
            gravity_y=-20.0,
            drag=0.5,
            start_size=(16.0, 24.0),
            end_size=(32.0, 48.0),
            start_color=(0.3, 0.3, 0.3, 0.5),
            end_color=(0.5, 0.5, 0.5, 0.0),
        )

    @staticmethod
    def sparkle() -> ParticleConfig:
        return ParticleConfig(
            lifetime=(0.3, 0.6),
            speed=(20.0, 50.0),
            direction=(0.0, 360.0),
            gravity_y=50.0,
            start_size=(4.0, 8.0),
            end_size=(2.0, 4.0),
            start_color=(1.0, 1.0, 0.8, 1.0),
            end_color=(1.0, 0.8, 0.4, 0.0),
            blend_mode=BlendMode.ADDITIVE,
        )

    @staticmethod
    def rain() -> ParticleConfig:
        return ParticleConfig(
            lifetime=(0.5, 1.0),
            speed=(400.0, 600.0),
            direction=(250.0, 260.0),
            start_size=(2.0, 4.0),
            end_size=(2.0, 4.0),
            start_color=(0.7, 0.8, 1.0, 0.6),
            end_color=(0.7, 0.8, 1.0, 0.0),
        )

    @staticmethod
    def dust() -> ParticleConfig:
        return ParticleConfig(
            lifetime=(1.0, 2.0),
            speed=(5.0, 15.0),
            direction=(0.0, 360.0),
            gravity_y=-5.0,
            start_size=(2.0, 4.0),
            end_size=(1.0, 2.0),
            start_color=(0.8, 0.7, 0.6, 0.4),
            end_color=(0.8, 0.7, 0.6, 0.0),
        )

    @staticmethod
    def magic() -> ParticleConfig:
        return ParticleConfig(
            lifetime=(0.5, 1.5),
            speed=(30.0, 80.0),
            direction=(0.0, 360.0),
            drag=0.8,
            start_size=(8.0, 16.0),
            end_size=(2.0, 4.0),
            start_color=(0.5, 0.8, 1.0, 1.0),
            end_color=(0.8, 0.4, 1.0, 0.0),
            rotation_speed=(-180.0, 180.0),
            blend_mode=BlendMode.ADDITIVE,
        )
