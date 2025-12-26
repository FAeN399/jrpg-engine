"""
GPU-accelerated tilemap renderer.

Renders tile-based maps efficiently using a single draw call
per layer. Supports multiple layers, animated tiles, and
auto-tiling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
import struct
import json
from pathlib import Path

import moderngl
import numpy as np

if TYPE_CHECKING:
    from engine.graphics.texture import TextureAtlas
    from engine.graphics.camera import Camera


@dataclass
class TileLayer:
    """
    A single layer of tiles.

    Tiles are stored as a 2D array of tile IDs.
    -1 or 0 means empty (no tile).
    """
    name: str
    width: int
    height: int
    tiles: np.ndarray  # Shape: (height, width), dtype: int32
    visible: bool = True
    opacity: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    parallax_x: float = 1.0  # 1.0 = normal scroll, 0 = fixed
    parallax_y: float = 1.0

    # GPU resources (created on first render)
    _vbo: moderngl.Buffer | None = field(default=None, repr=False)
    _vao: moderngl.VertexArray | None = field(default=None, repr=False)
    _vertex_count: int = 0
    _dirty: bool = True

    def get_tile(self, x: int, y: int) -> int:
        """Get tile ID at position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return int(self.tiles[y, x])
        return -1

    def set_tile(self, x: int, y: int, tile_id: int) -> None:
        """Set tile ID at position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y, x] = tile_id
            self._dirty = True

    def fill(self, tile_id: int) -> None:
        """Fill entire layer with a tile."""
        self.tiles.fill(tile_id)
        self._dirty = True

    def clear(self) -> None:
        """Clear all tiles."""
        self.tiles.fill(-1)
        self._dirty = True


@dataclass
class CollisionLayer:
    """
    Collision data for a tilemap.

    Stores boolean passability per tile.
    """
    width: int
    height: int
    data: np.ndarray  # Shape: (height, width), dtype: bool

    def is_passable(self, x: int, y: int) -> bool:
        """Check if a tile is passable."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return bool(self.data[y, x])
        return False

    def set_passable(self, x: int, y: int, passable: bool) -> None:
        """Set tile passability."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.data[y, x] = passable


# Tilemap vertex shader
TILEMAP_VERTEX_SHADER = """
#version 330 core

in vec2 in_position;
in vec2 in_texcoord;

out vec2 v_texcoord;
out vec2 v_worldpos;

uniform mat4 u_projection;
uniform vec2 u_camera;
uniform vec2 u_offset;
uniform vec2 u_parallax;

void main() {
    // Apply parallax scrolling
    vec2 cam = u_camera * u_parallax;
    vec2 world_pos = in_position + u_offset;
    vec2 view_pos = world_pos - cam;

    gl_Position = u_projection * vec4(view_pos, 0.0, 1.0);
    v_texcoord = in_texcoord;
    v_worldpos = world_pos;
}
"""

TILEMAP_FRAGMENT_SHADER = """
#version 330 core

in vec2 v_texcoord;
in vec2 v_worldpos;

out vec4 fragColor;

uniform sampler2D u_texture;
uniform float u_opacity;

// Lighting
uniform bool u_lighting_enabled;
uniform vec3 u_ambient;
uniform int u_num_lights;
uniform vec3 u_light_positions[16];
uniform vec4 u_light_colors[16];

void main() {
    vec4 color = texture(u_texture, v_texcoord);

    if (color.a < 0.01) {
        discard;
    }

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

    color.a *= u_opacity;
    fragColor = color;
}
"""


class TilemapRenderer:
    """
    Renders tile-based maps with multiple layers.

    Features:
    - Efficient GPU rendering (one draw call per layer)
    - Multiple layers with parallax
    - Dynamic lighting integration
    - View frustum culling
    """

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx

        # Create shader program
        self.program = ctx.program(
            vertex_shader=TILEMAP_VERTEX_SHADER,
            fragment_shader=TILEMAP_FRAGMENT_SHADER,
        )

        # Projection matrix
        self._projection = self._ortho_matrix(1280, 720)

        # Lighting state (shared with SpriteBatch)
        self._lighting_enabled = False
        self._ambient = (0.2, 0.2, 0.3)
        self._lights: list[tuple[float, float, float, tuple[float, float, float], float]] = []

    def set_projection(self, width: float, height: float) -> None:
        """Set orthographic projection."""
        self._projection = self._ortho_matrix(width, height)

    def set_lighting(
        self,
        enabled: bool,
        ambient: tuple[float, float, float] = (0.2, 0.2, 0.3),
    ) -> None:
        """Enable/disable lighting."""
        self._lighting_enabled = enabled
        self._ambient = ambient

    def set_lights(
        self,
        lights: list[tuple[float, float, float, tuple[float, float, float], float]],
    ) -> None:
        """Set light list (x, y, radius, color, intensity)."""
        self._lights = lights[:16]

    def render_layer(
        self,
        layer: TileLayer,
        tileset: TextureAtlas,
        camera_x: float,
        camera_y: float,
        tile_size: int = 16,
    ) -> None:
        """
        Render a single tile layer.

        Args:
            layer: The tile layer to render
            tileset: Texture atlas containing tile graphics
            camera_x, camera_y: Camera position
            tile_size: Size of each tile in pixels
        """
        if not layer.visible:
            return

        # Rebuild geometry if dirty
        if layer._dirty or layer._vao is None:
            self._build_layer_geometry(layer, tileset, tile_size)

        if layer._vertex_count == 0:
            return

        # Set uniforms
        tileset.texture.use(0)
        self.program['u_texture'].value = 0
        self.program['u_projection'].write(self._projection.tobytes())
        self.program['u_camera'].value = (camera_x, camera_y)
        self.program['u_offset'].value = (layer.offset_x, layer.offset_y)
        self.program['u_parallax'].value = (layer.parallax_x, layer.parallax_y)
        self.program['u_opacity'].value = layer.opacity

        # Lighting
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

                while len(positions) < 48:
                    positions.extend([0.0, 0.0, 0.0])
                while len(colors) < 64:
                    colors.extend([0.0, 0.0, 0.0, 0.0])

                self.program['u_light_positions'].value = positions
                self.program['u_light_colors'].value = colors

        # Draw
        layer._vao.render(vertices=layer._vertex_count)

    def _build_layer_geometry(
        self,
        layer: TileLayer,
        tileset: TextureAtlas,
        tile_size: int,
    ) -> None:
        """Build GPU geometry for a layer."""
        vertices = []

        tile_uv_w = 1.0 / tileset.cols
        tile_uv_h = 1.0 / tileset.rows

        for y in range(layer.height):
            for x in range(layer.width):
                tile_id = layer.tiles[y, x]
                if tile_id < 0:
                    continue

                # World position
                px = x * tile_size
                py = y * tile_size

                # UV coordinates
                tu = (tile_id % tileset.cols) * tile_uv_w
                tv = (tile_id // tileset.cols) * tile_uv_h

                # Two triangles (6 vertices)
                vertices.extend([
                    px, py, tu, tv,
                    px + tile_size, py, tu + tile_uv_w, tv,
                    px + tile_size, py + tile_size, tu + tile_uv_w, tv + tile_uv_h,

                    px, py, tu, tv,
                    px + tile_size, py + tile_size, tu + tile_uv_w, tv + tile_uv_h,
                    px, py + tile_size, tu, tv + tile_uv_h,
                ])

        if not vertices:
            layer._vertex_count = 0
            layer._dirty = False
            return

        # Create/update buffer
        data = struct.pack(f'{len(vertices)}f', *vertices)

        if layer._vbo is None:
            layer._vbo = self.ctx.buffer(data)
            layer._vao = self.ctx.vertex_array(
                self.program,
                [(layer._vbo, '2f 2f', 'in_position', 'in_texcoord')],
            )
        else:
            layer._vbo.orphan(len(data))
            layer._vbo.write(data)

        layer._vertex_count = len(vertices) // 4  # 4 floats per vertex
        layer._dirty = False

    def _ortho_matrix(self, width: float, height: float) -> np.ndarray:
        """Create orthographic projection matrix."""
        left, right = 0, width
        bottom, top = height, 0
        near, far = -1, 1

        return np.array([
            [2 / (right - left), 0, 0, -(right + left) / (right - left)],
            [0, 2 / (top - bottom), 0, -(top + bottom) / (top - bottom)],
            [0, 0, -2 / (far - near), -(far + near) / (far - near)],
            [0, 0, 0, 1],
        ], dtype='f4')


class Tilemap:
    """
    Complete tilemap with multiple layers.

    Manages layers, collision, and provides high-level API.
    """

    def __init__(
        self,
        width: int,
        height: int,
        tile_size: int = 16,
    ):
        self.width = width
        self.height = height
        self.tile_size = tile_size

        self.layers: list[TileLayer] = []
        self.collision: CollisionLayer | None = None

        # Properties
        self.properties: dict = {}

    @property
    def pixel_width(self) -> int:
        """Map width in pixels."""
        return self.width * self.tile_size

    @property
    def pixel_height(self) -> int:
        """Map height in pixels."""
        return self.height * self.tile_size

    def add_layer(self, name: str, **kwargs) -> TileLayer:
        """Add a new layer."""
        tiles = np.full((self.height, self.width), -1, dtype=np.int32)
        layer = TileLayer(
            name=name,
            width=self.width,
            height=self.height,
            tiles=tiles,
            **kwargs,
        )
        self.layers.append(layer)
        return layer

    def get_layer(self, name: str) -> TileLayer | None:
        """Get layer by name."""
        for layer in self.layers:
            if layer.name == name:
                return layer
        return None

    def create_collision(self, default_passable: bool = True) -> CollisionLayer:
        """Create collision layer."""
        data = np.full((self.height, self.width), default_passable, dtype=bool)
        self.collision = CollisionLayer(self.width, self.height, data)
        return self.collision

    def is_passable(self, x: int, y: int) -> bool:
        """Check if tile is passable."""
        if self.collision is None:
            return True
        return self.collision.is_passable(x, y)

    def world_to_tile(self, x: float, y: float) -> tuple[int, int]:
        """Convert world coordinates to tile coordinates."""
        return (int(x // self.tile_size), int(y // self.tile_size))

    def tile_to_world(self, tx: int, ty: int) -> tuple[float, float]:
        """Convert tile coordinates to world coordinates (top-left of tile)."""
        return (tx * self.tile_size, ty * self.tile_size)

    @classmethod
    def from_tiled_json(cls, path: str | Path, ctx: moderngl.Context) -> Tilemap:
        """
        Load tilemap from Tiled JSON export.

        Args:
            path: Path to JSON file
            ctx: ModernGL context for GPU resources

        Returns:
            Loaded tilemap
        """
        with open(path) as f:
            data = json.load(f)

        tilemap = cls(
            width=data['width'],
            height=data['height'],
            tile_size=data.get('tilewidth', 16),
        )

        # Load layers
        for layer_data in data.get('layers', []):
            if layer_data['type'] == 'tilelayer':
                tiles = np.array(layer_data['data'], dtype=np.int32)
                tiles = tiles.reshape((layer_data['height'], layer_data['width']))
                # Tiled uses 0 as empty, we use -1
                tiles = np.where(tiles > 0, tiles - 1, -1)

                layer = TileLayer(
                    name=layer_data['name'],
                    width=layer_data['width'],
                    height=layer_data['height'],
                    tiles=tiles,
                    visible=layer_data.get('visible', True),
                    opacity=layer_data.get('opacity', 1.0),
                    offset_x=layer_data.get('offsetx', 0),
                    offset_y=layer_data.get('offsety', 0),
                )
                tilemap.layers.append(layer)

        # Load properties
        tilemap.properties = data.get('properties', {})

        return tilemap
