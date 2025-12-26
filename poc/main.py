"""
Phase 0: Proof of Concept
=========================
Validate that Pygame + ModernGL can render a lit tilemap at 60fps.

Controls:
- Arrow keys / WASD: Move light
- Mouse: Light follows cursor
- ESC: Quit
- L: Toggle light on/off
- +/-: Adjust light radius
"""

import sys
import math
import pygame
import moderngl
import numpy as np
from pathlib import Path

# Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
TILE_SIZE = 16
MAP_WIDTH = 80  # tiles
MAP_HEIGHT = 45  # tiles
SCALE = 1  # Render at native resolution, scale up

# Colors for procedural tileset
COLORS = {
    0: (34, 32, 52),     # void/black
    1: (69, 40, 60),     # dark ground
    2: (102, 57, 49),    # brown ground
    3: (143, 86, 59),    # light brown
    4: (89, 86, 82),     # stone
    5: (155, 173, 183),  # light stone
    6: (48, 96, 48),     # dark grass
    7: (75, 105, 47),    # grass
    8: (82, 127, 57),    # light grass
    9: (63, 63, 116),    # water dark
    10: (89, 125, 206),  # water
    11: (109, 170, 44),  # bright green
}


def create_procedural_tileset() -> bytes:
    """Create a simple 16x16 tileset procedurally."""
    tileset_width = 16 * 4  # 4 tiles wide
    tileset_height = 16 * 3  # 3 tiles tall
    data = np.zeros((tileset_height, tileset_width, 4), dtype=np.uint8)

    for tile_id, color in COLORS.items():
        tx = (tile_id % 4) * 16
        ty = (tile_id // 4) * 16
        if ty + 16 <= tileset_height and tx + 16 <= tileset_width:
            # Fill base color
            data[ty:ty+16, tx:tx+16, 0] = color[0]
            data[ty:ty+16, tx:tx+16, 1] = color[1]
            data[ty:ty+16, tx:tx+16, 2] = color[2]
            data[ty:ty+16, tx:tx+16, 3] = 255

            # Add some noise/variation
            noise = np.random.randint(-10, 10, (16, 16, 3))
            for c in range(3):
                channel = data[ty:ty+16, tx:tx+16, c].astype(np.int16)
                channel = np.clip(channel + noise[:, :, c], 0, 255)
                data[ty:ty+16, tx:tx+16, c] = channel.astype(np.uint8)

    return data.tobytes()


def create_procedural_map() -> np.ndarray:
    """Create a simple procedural map."""
    tilemap = np.zeros((MAP_HEIGHT, MAP_WIDTH), dtype=np.int32)

    # Fill with grass
    tilemap[:, :] = 7

    # Add some variation
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            r = np.random.random()
            if r < 0.1:
                tilemap[y, x] = 6  # dark grass
            elif r < 0.2:
                tilemap[y, x] = 8  # light grass
            elif r < 0.25:
                tilemap[y, x] = 11  # bright green

    # Add a stone path
    path_y = MAP_HEIGHT // 2
    for x in range(MAP_WIDTH):
        wave = int(math.sin(x * 0.2) * 2)
        for dy in range(-1, 2):
            py = path_y + wave + dy
            if 0 <= py < MAP_HEIGHT:
                tilemap[py, x] = 4 if dy == 0 else 5

    # Add water pond
    cx, cy = MAP_WIDTH // 4, MAP_HEIGHT // 3
    for y in range(cy - 5, cy + 5):
        for x in range(cx - 8, cx + 8):
            if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist < 6:
                    tilemap[y, x] = 10 if dist < 4 else 9

    return tilemap


# Vertex shader - handles sprite positioning and UV coordinates
VERTEX_SHADER = """
#version 330 core

in vec2 in_position;
in vec2 in_texcoord;

out vec2 v_texcoord;
out vec2 v_worldpos;

uniform vec2 u_resolution;
uniform vec2 u_camera;

void main() {
    vec2 pos = in_position - u_camera;
    vec2 ndc = (pos / u_resolution) * 2.0 - 1.0;
    ndc.y = -ndc.y;  // Flip Y for screen coordinates
    gl_Position = vec4(ndc, 0.0, 1.0);
    v_texcoord = in_texcoord;
    v_worldpos = in_position;
}
"""

# Fragment shader - handles texturing and lighting
FRAGMENT_SHADER = """
#version 330 core

in vec2 v_texcoord;
in vec2 v_worldpos;

out vec4 fragColor;

uniform sampler2D u_texture;
uniform vec2 u_light_pos;
uniform float u_light_radius;
uniform vec3 u_light_color;
uniform float u_light_intensity;
uniform vec3 u_ambient;
uniform bool u_light_enabled;

void main() {
    vec4 texColor = texture(u_texture, v_texcoord);

    if (texColor.a < 0.1) {
        discard;
    }

    vec3 finalColor = texColor.rgb;

    if (u_light_enabled) {
        // Calculate distance to light
        float dist = distance(v_worldpos, u_light_pos);

        // Smooth falloff
        float attenuation = 1.0 - smoothstep(0.0, u_light_radius, dist);
        attenuation = attenuation * attenuation;  // Quadratic falloff for nicer look

        // Apply lighting
        vec3 light = u_ambient + u_light_color * u_light_intensity * attenuation;
        finalColor = texColor.rgb * light;
    }

    fragColor = vec4(finalColor, texColor.a);
}
"""

# Post-processing bloom shader (simple version)
BLOOM_VERTEX = """
#version 330 core

in vec2 in_position;
in vec2 in_texcoord;

out vec2 v_texcoord;

void main() {
    gl_Position = vec4(in_position, 0.0, 1.0);
    v_texcoord = in_texcoord;
}
"""

BLOOM_FRAGMENT = """
#version 330 core

in vec2 v_texcoord;
out vec4 fragColor;

uniform sampler2D u_texture;
uniform vec2 u_resolution;
uniform float u_bloom_intensity;

void main() {
    vec4 color = texture(u_texture, v_texcoord);

    // Simple box blur for bloom effect
    vec2 texel = 1.0 / u_resolution;
    vec3 bloom = vec3(0.0);

    // Sample surrounding pixels
    for (int x = -2; x <= 2; x++) {
        for (int y = -2; y <= 2; y++) {
            vec2 offset = vec2(float(x), float(y)) * texel * 2.0;
            vec3 sample_color = texture(u_texture, v_texcoord + offset).rgb;
            // Only bloom bright pixels
            float brightness = dot(sample_color, vec3(0.2126, 0.7152, 0.0722));
            if (brightness > 0.7) {
                bloom += sample_color;
            }
        }
    }
    bloom /= 25.0;

    fragColor = vec4(color.rgb + bloom * u_bloom_intensity, color.a);
}
"""


class POCRenderer:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("JRPG Engine - Phase 0 POC")

        # Create window with OpenGL context
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK,
                                        pygame.GL_CONTEXT_PROFILE_CORE)

        self.screen = pygame.display.set_mode(
            (SCREEN_WIDTH, SCREEN_HEIGHT),
            pygame.OPENGL | pygame.DOUBLEBUF
        )

        # Create ModernGL context
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        # Create shaders
        self.program = self.ctx.program(
            vertex_shader=VERTEX_SHADER,
            fragment_shader=FRAGMENT_SHADER,
        )

        self.bloom_program = self.ctx.program(
            vertex_shader=BLOOM_VERTEX,
            fragment_shader=BLOOM_FRAGMENT,
        )

        # Create tileset texture
        self.tileset = self._create_tileset_texture()

        # Create map
        self.tilemap = create_procedural_map()

        # Create vertex buffer for tiles
        self.tile_vbo, self.tile_vao = self._create_tile_geometry()

        # Create framebuffer for post-processing
        self.fbo_texture = self.ctx.texture((SCREEN_WIDTH, SCREEN_HEIGHT), 4)
        self.fbo = self.ctx.framebuffer(color_attachments=[self.fbo_texture])

        # Create fullscreen quad for post-processing
        self.quad_vbo, self.quad_vao = self._create_fullscreen_quad()

        # Light properties
        self.light_pos = [SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2]
        self.light_radius = 200.0
        self.light_color = [1.0, 0.9, 0.7]  # Warm light
        self.light_intensity = 1.5
        self.light_enabled = True

        # Camera
        self.camera = [0.0, 0.0]

        # Stats
        self.clock = pygame.time.Clock()
        self.frame_times = []

    def _create_tileset_texture(self) -> moderngl.Texture:
        """Create GPU texture from procedural tileset."""
        data = create_procedural_tileset()
        texture = self.ctx.texture((64, 48), 4, data)
        texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        return texture

    def _create_tile_geometry(self) -> tuple:
        """Create vertex buffer for all tiles in the map."""
        vertices = []

        tileset_cols = 4
        tile_uv_w = 1.0 / tileset_cols
        tile_uv_h = 1.0 / 3  # 3 rows in tileset

        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                tile_id = self.tilemap[y, x]

                # World position
                px = x * TILE_SIZE
                py = y * TILE_SIZE

                # UV coordinates
                tu = (tile_id % tileset_cols) * tile_uv_w
                tv = (tile_id // tileset_cols) * tile_uv_h

                # Two triangles per tile (6 vertices)
                # Triangle 1
                vertices.extend([
                    px, py, tu, tv,
                    px + TILE_SIZE, py, tu + tile_uv_w, tv,
                    px + TILE_SIZE, py + TILE_SIZE, tu + tile_uv_w, tv + tile_uv_h,
                ])
                # Triangle 2
                vertices.extend([
                    px, py, tu, tv,
                    px + TILE_SIZE, py + TILE_SIZE, tu + tile_uv_w, tv + tile_uv_h,
                    px, py + TILE_SIZE, tu, tv + tile_uv_h,
                ])

        vertices = np.array(vertices, dtype='f4')
        vbo = self.ctx.buffer(vertices.tobytes())
        vao = self.ctx.vertex_array(
            self.program,
            [(vbo, '2f 2f', 'in_position', 'in_texcoord')]
        )
        return vbo, vao

    def _create_fullscreen_quad(self) -> tuple:
        """Create fullscreen quad for post-processing."""
        vertices = np.array([
            # position    texcoord
            -1.0, -1.0,   0.0, 0.0,
             1.0, -1.0,   1.0, 0.0,
             1.0,  1.0,   1.0, 1.0,
            -1.0, -1.0,   0.0, 0.0,
             1.0,  1.0,   1.0, 1.0,
            -1.0,  1.0,   0.0, 1.0,
        ], dtype='f4')

        vbo = self.ctx.buffer(vertices.tobytes())
        vao = self.ctx.vertex_array(
            self.bloom_program,
            [(vbo, '2f 2f', 'in_position', 'in_texcoord')]
        )
        return vbo, vao

    def update(self, dt: float):
        """Update game state."""
        # Light follows mouse
        mx, my = pygame.mouse.get_pos()
        self.light_pos = [float(mx) + self.camera[0], float(my) + self.camera[1]]

        # Keyboard controls for camera
        keys = pygame.key.get_pressed()
        cam_speed = 300 * dt

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.camera[0] -= cam_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.camera[0] += cam_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.camera[1] -= cam_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.camera[1] += cam_speed

        # Clamp camera
        max_x = MAP_WIDTH * TILE_SIZE - SCREEN_WIDTH
        max_y = MAP_HEIGHT * TILE_SIZE - SCREEN_HEIGHT
        self.camera[0] = max(0, min(self.camera[0], max_x))
        self.camera[1] = max(0, min(self.camera[1], max_y))

    def render(self):
        """Render the scene."""
        # Render to framebuffer
        self.fbo.use()
        self.ctx.clear(0.1, 0.1, 0.15, 1.0)

        # Set uniforms for main shader
        self.tileset.use(0)
        self.program['u_texture'].value = 0
        self.program['u_resolution'].value = (SCREEN_WIDTH, SCREEN_HEIGHT)
        self.program['u_camera'].value = tuple(self.camera)
        self.program['u_light_pos'].value = tuple(self.light_pos)
        self.program['u_light_radius'].value = self.light_radius
        self.program['u_light_color'].value = tuple(self.light_color)
        self.program['u_light_intensity'].value = self.light_intensity
        self.program['u_ambient'].value = (0.2, 0.2, 0.3)  # Slight blue ambient
        self.program['u_light_enabled'].value = self.light_enabled

        # Draw tiles
        self.tile_vao.render()

        # Post-processing pass
        self.ctx.screen.use()
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)

        self.fbo_texture.use(0)
        self.bloom_program['u_texture'].value = 0
        self.bloom_program['u_resolution'].value = (SCREEN_WIDTH, SCREEN_HEIGHT)
        self.bloom_program['u_bloom_intensity'].value = 0.3

        self.quad_vao.render()

        pygame.display.flip()

    def run(self):
        """Main loop."""
        running = True

        while running:
            dt = self.clock.tick(60) / 1000.0

            # Track frame times
            self.frame_times.append(dt)
            if len(self.frame_times) > 60:
                self.frame_times.pop(0)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_l:
                        self.light_enabled = not self.light_enabled
                    elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                        self.light_radius = min(500, self.light_radius + 20)
                    elif event.key == pygame.K_MINUS:
                        self.light_radius = max(50, self.light_radius - 20)

            self.update(dt)
            self.render()

            # Update title with FPS
            avg_dt = sum(self.frame_times) / len(self.frame_times)
            fps = 1.0 / avg_dt if avg_dt > 0 else 0
            pygame.display.set_caption(
                f"JRPG Engine POC | FPS: {fps:.1f} | "
                f"Light: {'ON' if self.light_enabled else 'OFF'} | "
                f"Radius: {self.light_radius:.0f} | "
                f"WASD/Arrows: Move Camera | Mouse: Light Position"
            )

        # Print final stats
        avg_dt = sum(self.frame_times) / len(self.frame_times)
        print(f"\n=== POC Results ===")
        print(f"Average FPS: {1.0/avg_dt:.1f}")
        print(f"Average frame time: {avg_dt*1000:.2f}ms")
        print(f"Tiles rendered: {MAP_WIDTH * MAP_HEIGHT} ({MAP_WIDTH}x{MAP_HEIGHT})")
        print(f"Vertices per frame: {MAP_WIDTH * MAP_HEIGHT * 6}")

        if avg_dt <= 1/60:
            print("\n[SUCCESS] Rendering at 60+ FPS - Proof of concept PASSED!")
        else:
            print("\n[WARNING] Below 60 FPS - May need optimization")

        pygame.quit()


if __name__ == "__main__":
    try:
        renderer = POCRenderer()
        renderer.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)
