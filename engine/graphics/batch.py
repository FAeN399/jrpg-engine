"""
Sprite batch renderer for efficient GPU rendering.

Batches multiple sprites into a single draw call for performance.
Uses GPU instancing when possible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
import struct

import moderngl
import numpy as np

if TYPE_CHECKING:
    from engine.graphics.texture import TextureRegion


# Batch vertex shader
BATCH_VERTEX_SHADER = """
#version 330 core

in vec2 in_position;
in vec2 in_texcoord;
in vec4 in_color;

out vec2 v_texcoord;
out vec4 v_color;
out vec2 v_worldpos;

uniform mat4 u_projection;
uniform vec2 u_camera;

void main() {
    vec2 world_pos = in_position;
    v_worldpos = world_pos;

    // Apply camera offset
    vec2 view_pos = world_pos - u_camera;

    gl_Position = u_projection * vec4(view_pos, 0.0, 1.0);
    v_texcoord = in_texcoord;
    v_color = in_color;
}
"""

# Batch fragment shader (with lighting support)
BATCH_FRAGMENT_SHADER = """
#version 330 core

in vec2 v_texcoord;
in vec4 v_color;
in vec2 v_worldpos;

out vec4 fragColor;

uniform sampler2D u_texture;

// Lighting uniforms (optional)
uniform bool u_lighting_enabled;
uniform vec3 u_ambient;
uniform int u_num_lights;
uniform vec3 u_light_positions[16];  // xy = position, z = radius
uniform vec4 u_light_colors[16];     // rgb = color, a = intensity

void main() {
    vec4 tex_color = texture(u_texture, v_texcoord);

    if (tex_color.a < 0.01) {
        discard;
    }

    vec4 color = tex_color * v_color;

    if (u_lighting_enabled && u_num_lights > 0) {
        vec3 light = u_ambient;

        for (int i = 0; i < u_num_lights && i < 16; i++) {
            vec2 light_pos = u_light_positions[i].xy;
            float radius = u_light_positions[i].z;
            vec3 light_color = u_light_colors[i].rgb;
            float intensity = u_light_colors[i].a;

            float dist = distance(v_worldpos, light_pos);
            float attenuation = 1.0 - smoothstep(0.0, radius, dist);
            attenuation = attenuation * attenuation;

            light += light_color * intensity * attenuation;
        }

        color.rgb *= light;
    }

    fragColor = color;
}
"""


@dataclass
class Sprite:
    """
    Sprite data for batching.

    All fields are in world coordinates.
    """
    x: float
    y: float
    width: float
    height: float
    u0: float = 0.0
    v0: float = 0.0
    u1: float = 1.0
    v1: float = 1.0
    r: float = 1.0
    g: float = 1.0
    b: float = 1.0
    a: float = 1.0
    rotation: float = 0.0  # Radians
    origin_x: float = 0.5  # 0-1, relative to width
    origin_y: float = 0.5  # 0-1, relative to height

    @classmethod
    def from_region(
        cls,
        region: TextureRegion,
        x: float,
        y: float,
        scale: float = 1.0,
        color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
        rotation: float = 0.0,
        origin: tuple[float, float] = (0.5, 0.5),
    ) -> Sprite:
        """Create sprite from a texture region."""
        return cls(
            x=x, y=y,
            width=region.width * scale,
            height=region.height * scale,
            u0=region.u0, v0=region.v0,
            u1=region.u1, v1=region.v1,
            r=color[0], g=color[1], b=color[2], a=color[3],
            rotation=rotation,
            origin_x=origin[0], origin_y=origin[1],
        )


class SpriteBatch:
    """
    Batched sprite renderer.

    Collects sprites and renders them in a single draw call.
    Automatically handles texture changes by flushing the batch.

    Usage:
        batch.begin()
        batch.draw(sprite1)
        batch.draw(sprite2)
        batch.draw_region(region, x, y)
        batch.end()
    """

    # Maximum sprites per batch (65536 vertices / 4 vertices per sprite)
    MAX_SPRITES = 16384

    # Vertex format: position(2) + texcoord(2) + color(4) = 8 floats
    VERTEX_SIZE = 8
    FLOATS_PER_SPRITE = 6 * VERTEX_SIZE  # 6 vertices per sprite (2 triangles)

    def __init__(self, ctx: moderngl.Context, max_sprites: int = MAX_SPRITES):
        self.ctx = ctx
        self.max_sprites = max_sprites

        # Create shader program
        self.program = ctx.program(
            vertex_shader=BATCH_VERTEX_SHADER,
            fragment_shader=BATCH_FRAGMENT_SHADER,
        )

        # Create vertex buffer (dynamic)
        buffer_size = max_sprites * self.FLOATS_PER_SPRITE * 4  # 4 bytes per float
        self.vbo = ctx.buffer(reserve=buffer_size, dynamic=True)

        # Create vertex array
        self.vao = ctx.vertex_array(
            self.program,
            [(self.vbo, '2f 2f 4f', 'in_position', 'in_texcoord', 'in_color')],
        )

        # Batch state
        self._vertices: list[float] = []
        self._sprite_count = 0
        self._current_texture: moderngl.Texture | None = None
        self._drawing = False

        # Projection matrix (will be set by camera)
        self._projection = self._ortho_matrix(1280, 720)

        # Camera offset
        self._camera_x = 0.0
        self._camera_y = 0.0

        # Lighting state
        self._lighting_enabled = False
        self._ambient = (0.2, 0.2, 0.3)
        self._lights: list[tuple[float, float, float, tuple[float, float, float], float]] = []

    def begin(self, texture: moderngl.Texture | None = None) -> None:
        """
        Begin a new batch.

        Args:
            texture: Optional texture to use
        """
        if self._drawing:
            raise RuntimeError("SpriteBatch.begin() called while already drawing")

        self._drawing = True
        self._vertices.clear()
        self._sprite_count = 0
        self._current_texture = texture

    def end(self) -> None:
        """End the batch and render all sprites."""
        if not self._drawing:
            raise RuntimeError("SpriteBatch.end() called without begin()")

        self._flush()
        self._drawing = False

    def set_projection(self, width: float, height: float) -> None:
        """Set orthographic projection matrix."""
        self._projection = self._ortho_matrix(width, height)

    def set_camera(self, x: float, y: float) -> None:
        """Set camera offset."""
        self._camera_x = x
        self._camera_y = y

    def set_lighting(
        self,
        enabled: bool,
        ambient: tuple[float, float, float] = (0.2, 0.2, 0.3),
    ) -> None:
        """Enable/disable lighting."""
        self._lighting_enabled = enabled
        self._ambient = ambient

    def add_light(
        self,
        x: float,
        y: float,
        radius: float,
        color: tuple[float, float, float] = (1.0, 1.0, 1.0),
        intensity: float = 1.0,
    ) -> None:
        """Add a point light for this frame."""
        if len(self._lights) < 16:
            self._lights.append((x, y, radius, color, intensity))

    def clear_lights(self) -> None:
        """Clear all lights."""
        self._lights.clear()

    def draw(self, sprite: Sprite, texture: moderngl.Texture | None = None) -> None:
        """
        Draw a sprite.

        Args:
            sprite: Sprite to draw
            texture: Texture to use (switches texture if different)
        """
        if not self._drawing:
            raise RuntimeError("SpriteBatch.draw() called without begin()")

        # Handle texture change
        if texture is not None and texture != self._current_texture:
            self._flush()
            self._current_texture = texture

        # Check if batch is full
        if self._sprite_count >= self.max_sprites:
            self._flush()

        # Generate vertices
        self._add_sprite_vertices(sprite)
        self._sprite_count += 1

    def draw_region(
        self,
        region: TextureRegion,
        x: float,
        y: float,
        width: float | None = None,
        height: float | None = None,
        color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
        rotation: float = 0.0,
        origin: tuple[float, float] = (0.5, 0.5),
    ) -> None:
        """
        Draw a texture region.

        Args:
            region: The texture region to draw
            x, y: Position
            width, height: Size (defaults to region size)
            color: RGBA color multiplier
            rotation: Rotation in radians
            origin: Origin point (0-1)
        """
        sprite = Sprite(
            x=x, y=y,
            width=width or region.width,
            height=height or region.height,
            u0=region.u0, v0=region.v0,
            u1=region.u1, v1=region.v1,
            r=color[0], g=color[1], b=color[2], a=color[3],
            rotation=rotation,
            origin_x=origin[0], origin_y=origin[1],
        )
        self.draw(sprite, region.texture)

    def draw_texture(
        self,
        texture: moderngl.Texture,
        x: float,
        y: float,
        width: float | None = None,
        height: float | None = None,
        color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    ) -> None:
        """Draw an entire texture."""
        w = width or texture.size[0]
        h = height or texture.size[1]

        sprite = Sprite(
            x=x, y=y,
            width=w, height=h,
            r=color[0], g=color[1], b=color[2], a=color[3],
        )
        self.draw(sprite, texture)

    def _add_sprite_vertices(self, sprite: Sprite) -> None:
        """Generate vertices for a sprite."""
        import math

        # Calculate corners relative to origin
        ox = sprite.origin_x * sprite.width
        oy = sprite.origin_y * sprite.height

        # Corner offsets (before rotation)
        x0, y0 = -ox, -oy
        x1, y1 = sprite.width - ox, -oy
        x2, y2 = sprite.width - ox, sprite.height - oy
        x3, y3 = -ox, sprite.height - oy

        # Apply rotation if needed
        if sprite.rotation != 0.0:
            cos_r = math.cos(sprite.rotation)
            sin_r = math.sin(sprite.rotation)

            def rotate(x, y):
                return x * cos_r - y * sin_r, x * sin_r + y * cos_r

            x0, y0 = rotate(x0, y0)
            x1, y1 = rotate(x1, y1)
            x2, y2 = rotate(x2, y2)
            x3, y3 = rotate(x3, y3)

        # Translate to world position
        x0 += sprite.x
        y0 += sprite.y
        x1 += sprite.x
        y1 += sprite.y
        x2 += sprite.x
        y2 += sprite.y
        x3 += sprite.x
        y3 += sprite.y

        # UV coordinates
        u0, v0 = sprite.u0, sprite.v0
        u1, v1 = sprite.u1, sprite.v1

        # Color
        r, g, b, a = sprite.r, sprite.g, sprite.b, sprite.a

        # Add two triangles (6 vertices)
        # Triangle 1: top-left, top-right, bottom-right
        self._vertices.extend([
            x0, y0, u0, v0, r, g, b, a,
            x1, y1, u1, v0, r, g, b, a,
            x2, y2, u1, v1, r, g, b, a,
        ])
        # Triangle 2: top-left, bottom-right, bottom-left
        self._vertices.extend([
            x0, y0, u0, v0, r, g, b, a,
            x2, y2, u1, v1, r, g, b, a,
            x3, y3, u0, v1, r, g, b, a,
        ])

    def _flush(self) -> None:
        """Flush the current batch to GPU."""
        if self._sprite_count == 0:
            return

        if self._current_texture is None:
            self._vertices.clear()
            self._sprite_count = 0
            return

        # Upload vertices
        data = struct.pack(f'{len(self._vertices)}f', *self._vertices)
        self.vbo.write(data)

        # Set uniforms
        self._current_texture.use(0)
        self.program['u_texture'].value = 0
        self.program['u_projection'].write(self._projection.tobytes())
        self.program['u_camera'].value = (self._camera_x, self._camera_y)

        # Lighting uniforms
        self.program['u_lighting_enabled'].value = self._lighting_enabled
        if self._lighting_enabled:
            self.program['u_ambient'].value = self._ambient
            self.program['u_num_lights'].value = len(self._lights)

            if self._lights:
                positions = []
                colors = []
                for x, y, radius, color, intensity in self._lights:
                    positions.extend([x, y, radius])
                    colors.extend([color[0], color[1], color[2], intensity])

                # Pad to 16 lights
                while len(positions) < 48:  # 16 * 3
                    positions.extend([0.0, 0.0, 0.0])
                while len(colors) < 64:  # 16 * 4
                    colors.extend([0.0, 0.0, 0.0, 0.0])

                self.program['u_light_positions'].value = positions
                self.program['u_light_colors'].value = colors

        # Draw
        self.vao.render(vertices=self._sprite_count * 6)

        # Reset
        self._vertices.clear()
        self._sprite_count = 0

    def _ortho_matrix(self, width: float, height: float) -> np.ndarray:
        """Create orthographic projection matrix."""
        left, right = 0, width
        bottom, top = height, 0  # Flip Y for screen coordinates
        near, far = -1, 1

        matrix = np.array([
            [2 / (right - left), 0, 0, -(right + left) / (right - left)],
            [0, 2 / (top - bottom), 0, -(top + bottom) / (top - bottom)],
            [0, 0, -2 / (far - near), -(far + near) / (far - near)],
            [0, 0, 0, 1],
        ], dtype='f4')

        return matrix
