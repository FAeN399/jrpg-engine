"""
Phase 2 Demo: GPU Rendering Pipeline

Demonstrates:
- Sprite batch rendering
- Tilemap with multiple layers
- Dynamic lighting with day/night cycle
- Particle effects
- Post-processing (bloom, vignette)
- Camera with follow and shake

Controls:
- WASD/Arrows: Move player
- Mouse: Light follows cursor
- L: Toggle lighting
- B: Toggle bloom
- V: Toggle vignette
- P: Spawn particles
- T: Advance time (day/night)
- Space: Camera shake
- +/-: Zoom
- ESC: Quit
"""

import math
import random
import struct

import pygame
import moderngl
import numpy as np

from engine.core import Game, GameConfig, Scene, Action
from engine.graphics import (
    SpriteBatch, Sprite, Camera, CameraBounds,
    TilemapRenderer, Tilemap, TileLayer, TextureAtlas,
    LightingSystem, PointLight,
    ParticleSystem, ParticleEmitter, ParticlePresets,
    PostProcessingChain,
)


def create_procedural_tileset(ctx: moderngl.Context, tile_size: int = 16) -> TextureAtlas:
    """Create a simple procedural tileset."""
    # Colors for different tile types
    colors = [
        (34, 32, 52),     # 0: void
        (69, 40, 60),     # 1: dark ground
        (102, 57, 49),    # 2: brown
        (143, 86, 59),    # 3: light brown
        (89, 86, 82),     # 4: stone
        (155, 173, 183),  # 5: light stone
        (48, 96, 48),     # 6: dark grass
        (75, 105, 47),    # 7: grass
        (82, 127, 57),    # 8: light grass
        (63, 63, 116),    # 9: water dark
        (89, 125, 206),   # 10: water
        (109, 170, 44),   # 11: bright green
    ]

    cols = 4
    rows = 3
    width = cols * tile_size
    height = rows * tile_size

    data = np.zeros((height, width, 4), dtype=np.uint8)

    for i, color in enumerate(colors):
        x = (i % cols) * tile_size
        y = (i // cols) * tile_size

        if y + tile_size <= height and x + tile_size <= width:
            # Fill with color
            data[y:y+tile_size, x:x+tile_size, 0] = color[0]
            data[y:y+tile_size, x:x+tile_size, 1] = color[1]
            data[y:y+tile_size, x:x+tile_size, 2] = color[2]
            data[y:y+tile_size, x:x+tile_size, 3] = 255

            # Add noise
            noise = np.random.randint(-15, 15, (tile_size, tile_size, 3))
            for c in range(3):
                channel = data[y:y+tile_size, x:x+tile_size, c].astype(np.int16)
                data[y:y+tile_size, x:x+tile_size, c] = np.clip(
                    channel + noise[:,:,c], 0, 255
                ).astype(np.uint8)

    # Flip vertically for OpenGL
    data = np.flipud(data)

    texture = ctx.texture((width, height), 4, data.tobytes())
    texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

    atlas = TextureAtlas(texture, tile_size, tile_size)
    return atlas


def create_procedural_map(width: int, height: int) -> Tilemap:
    """Create a procedural map."""
    tilemap = Tilemap(width, height, tile_size=16)

    # Ground layer
    ground = tilemap.add_layer("ground")
    ground.tiles.fill(7)  # Grass

    # Add variation
    for y in range(height):
        for x in range(width):
            r = random.random()
            if r < 0.1:
                ground.tiles[y, x] = 6  # Dark grass
            elif r < 0.2:
                ground.tiles[y, x] = 8  # Light grass
            elif r < 0.25:
                ground.tiles[y, x] = 11  # Bright

    # Add paths
    for x in range(width):
        y = height // 2 + int(math.sin(x * 0.2) * 3)
        for dy in range(-1, 2):
            if 0 <= y + dy < height:
                ground.tiles[y + dy, x] = 4 if dy == 0 else 5

    # Add water pond
    cx, cy = width // 4, height // 3
    for y in range(cy - 5, cy + 5):
        for x in range(cx - 8, cx + 8):
            if 0 <= x < width and 0 <= y < height:
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist < 5:
                    ground.tiles[y, x] = 10 if dist < 3 else 9

    # Decoration layer (sparse)
    decor = tilemap.add_layer("decor")
    for y in range(height):
        for x in range(width):
            if random.random() < 0.02 and ground.tiles[y, x] in [7, 8]:
                decor.tiles[y, x] = 11  # Flower/bush

    return tilemap


class Phase2DemoScene(Scene):
    """Demo scene showcasing Phase 2 graphics features."""

    def on_enter(self) -> None:
        super().on_enter()

        ctx = self.game.ctx
        width = self.game.width
        height = self.game.height

        # Create tileset and map
        self.tileset = create_procedural_tileset(ctx)
        self.tilemap = create_procedural_map(80, 45)

        # Renderers
        self.tilemap_renderer = TilemapRenderer(ctx)
        self.sprite_batch = SpriteBatch(ctx)
        self.particle_system = ParticleSystem(ctx)

        # Camera
        self.camera = Camera(width, height)
        self.camera.bounds = CameraBounds(
            left=0, top=0,
            right=self.tilemap.pixel_width,
            bottom=self.tilemap.pixel_height,
        )

        # Player
        self.player_x = 640.0
        self.player_y = 360.0
        self.player_speed = 200.0

        # Lighting
        self.lighting = LightingSystem()
        self.lighting.enable_day_night(12.0)  # Start at noon

        # Player light (torch)
        self.player_light = self.lighting.create_light(
            self.player_x, self.player_y,
            radius=180, color=(1.0, 0.8, 0.5), intensity=1.2,
            flicker=0.15,
        )

        # Some static lights
        self.lighting.create_light(300, 200, 120, (0.4, 0.6, 1.0), 0.8)
        self.lighting.create_light(800, 400, 150, (1.0, 0.4, 0.2), 1.0, flicker=0.2)

        # Mouse light
        self.mouse_light = self.lighting.create_light(
            width / 2, height / 2,
            radius=200, color=(1.0, 1.0, 0.9), intensity=1.5,
        )

        # Particles
        self.fire_emitter = ParticleEmitter(ParticlePresets.fire(), max_particles=500)
        self.fire_emitter.x = 800
        self.fire_emitter.y = 400
        self.fire_emitter.emit_rate = 30

        self.magic_emitter = ParticleEmitter(ParticlePresets.magic(), max_particles=300)
        self.magic_emitter.enabled = False

        # Post-processing
        self.postfx = PostProcessingChain(ctx, width, height)
        self.bloom = self.postfx.enable_bloom(threshold=0.6, intensity=0.4)
        self.vignette = self.postfx.enable_vignette(intensity=1.2, radius=0.6)

        # Render target
        self._scene_tex = ctx.texture((width, height), 4)
        self._scene_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self._scene_fbo = ctx.framebuffer(color_attachments=[self._scene_tex])

        # State
        self.time_speed = 0.0  # Hours per second

        print("Phase 2 Demo loaded!")
        print("Controls:")
        print("  WASD/Arrows: Move player")
        print("  Mouse: Light follows cursor")
        print("  L: Toggle lighting")
        print("  B: Toggle bloom")
        print("  V: Toggle vignette")
        print("  P: Spawn magic particles at player")
        print("  T: Advance time (day/night)")
        print("  Space: Camera shake")
        print("  +/-: Zoom")
        print("  ESC: Quit")

    def update(self, dt: float) -> None:
        input = self.game.input

        # Movement
        move = input.get_movement_vector()
        self.player_x += move[0] * self.player_speed * dt
        self.player_y += move[1] * self.player_speed * dt

        # Clamp to map
        self.player_x = max(16, min(self.player_x, self.tilemap.pixel_width - 16))
        self.player_y = max(16, min(self.player_y, self.tilemap.pixel_height - 16))

        # Update player light
        self.player_light.x = self.player_x
        self.player_light.y = self.player_y

        # Mouse light
        mx, my = input.mouse_pos
        world_x, world_y = self.camera.screen_to_world(mx, my)
        self.mouse_light.x = world_x
        self.mouse_light.y = world_y

        # Camera follow
        self.camera.follow(self.player_x, self.player_y, dt)
        self.camera.update(dt)

        # Lighting update
        if self.time_speed > 0:
            self.lighting.day_night.advance_time(dt, self.time_speed)
        self.lighting.update(dt)

        # Particles
        self.fire_emitter.update(dt)
        self.magic_emitter.update(dt)

        # Input handling
        if input.is_action_just_pressed(Action.CANCEL):
            self.game.quit()

        if input.is_key_just_pressed(pygame.K_l):
            self.lighting.enabled = not self.lighting.enabled
            print(f"Lighting: {'ON' if self.lighting.enabled else 'OFF'}")

        if input.is_key_just_pressed(pygame.K_b):
            self.bloom.enabled = not self.bloom.enabled
            print(f"Bloom: {'ON' if self.bloom.enabled else 'OFF'}")

        if input.is_key_just_pressed(pygame.K_v):
            self.vignette.enabled = not self.vignette.enabled
            print(f"Vignette: {'ON' if self.vignette.enabled else 'OFF'}")

        if input.is_key_just_pressed(pygame.K_p):
            self.magic_emitter.x = self.player_x
            self.magic_emitter.y = self.player_y
            self.magic_emitter.emit(20)
            print("Magic particles spawned!")

        if input.is_key_just_pressed(pygame.K_t):
            self.time_speed = 2.0 if self.time_speed == 0 else 0.0
            print(f"Time: {'RUNNING' if self.time_speed > 0 else 'PAUSED'}")

        if input.is_key_just_pressed(pygame.K_SPACE):
            self.camera.shake(15, 0.3)
            print("Camera shake!")

        if input.is_key_just_pressed(pygame.K_EQUALS):
            self.camera.zoom_in(0.2)
        if input.is_key_just_pressed(pygame.K_MINUS):
            self.camera.zoom_out(0.2)

    def render(self, alpha: float) -> None:
        ctx = self.game.ctx

        # Render to scene buffer
        self._scene_fbo.use()
        ctx.clear(0.1, 0.1, 0.15, 1.0)

        cam_x, cam_y = self.camera.x, self.camera.y
        view_w, view_h = self.camera.scaled_width, self.camera.scaled_height

        # Apply lighting to renderers
        self.lighting.apply_to_tilemap(
            self.tilemap_renderer, cam_x, cam_y, view_w, view_h
        )
        self.tilemap_renderer.set_projection(view_w, view_h)

        # Render tilemap layers
        for layer in self.tilemap.layers:
            self.tilemap_renderer.render_layer(
                layer, self.tileset, cam_x, cam_y, self.tilemap.tile_size
            )

        # Render sprites
        self.lighting.apply_to_batch(
            self.sprite_batch, cam_x, cam_y, view_w, view_h
        )
        self.sprite_batch.set_projection(view_w, view_h)
        self.sprite_batch.set_camera(cam_x, cam_y)

        self.sprite_batch.begin(self.tileset.texture)

        # Draw player (simple colored square)
        player_region = self.tileset.get_region(3, 0)  # Light brown
        self.sprite_batch.draw_region(
            player_region,
            self.player_x - 12, self.player_y - 12,
            width=24, height=24,
            color=(0.8, 0.9, 1.0, 1.0),
        )

        self.sprite_batch.end()

        # Render particles (no lighting for additive particles)
        self.particle_system.set_projection(view_w, view_h)
        self.particle_system.set_camera(cam_x, cam_y)
        self.particle_system.render(self.fire_emitter, self.magic_emitter)

        # Apply post-processing
        self.postfx.process(self._scene_tex, ctx.screen)

        # Draw UI (directly to screen, no post-processing)
        self._draw_ui()

        pygame.display.flip()

    def _draw_ui(self) -> None:
        """Draw debug UI."""
        # We'd need a text rendering system for this
        # For now, just update window title
        hour = self.lighting.day_night.current_hour if self.lighting.day_night else 12
        pygame.display.set_caption(
            f"Phase 2 Demo | FPS: {self.game.fps:.0f} | "
            f"Time: {int(hour):02d}:{int((hour % 1) * 60):02d} | "
            f"Zoom: {self.camera.zoom:.1f}x | "
            f"Particles: {len(self.fire_emitter.particles) + len(self.magic_emitter.particles)}"
        )


def main():
    print("=" * 60)
    print("Phase 2 Demo: GPU Rendering Pipeline")
    print("=" * 60)
    print()

    config = GameConfig(
        title="JRPG Engine - Phase 2 Demo",
        width=1280,
        height=720,
        target_fps=60,
    )

    game = Game(config)
    game.debug_mode = True
    game.scene_manager.push(Phase2DemoScene(game))

    print("Starting demo...")
    game.run()
    print("Demo complete!")


if __name__ == "__main__":
    main()
