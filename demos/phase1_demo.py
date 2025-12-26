"""
Phase 1 Demo: Core Engine Skeleton

Demonstrates:
- Game loop with fixed timestep
- Scene management
- Entity-Component-System architecture
- Event bus
- Action-based input

Run: python -m demos.phase1_demo
"""

import math
import pygame
import moderngl

from engine.core import (
    Game, GameConfig, Scene, Entity, Component, System, RenderSystem,
    World, Action, register_component
)


# ============================================================================
# COMPONENTS (Data Only)
# ============================================================================

@register_component
class Transform(Component):
    """Position and rotation."""
    x: float = 0.0
    y: float = 0.0
    prev_x: float = 0.0  # For interpolation
    prev_y: float = 0.0
    rotation: float = 0.0


@register_component
class Velocity(Component):
    """Movement velocity."""
    vx: float = 0.0
    vy: float = 0.0


@register_component
class PlayerControlled(Component):
    """Marks entity as player-controlled."""
    speed: float = 200.0


@register_component
class Renderable(Component):
    """Visual representation."""
    color: tuple[int, int, int] = (255, 255, 255)
    size: float = 20.0
    shape: str = "circle"  # circle, square


# ============================================================================
# SYSTEMS (Logic Only)
# ============================================================================

class PlayerInputSystem(System):
    """Reads player input and sets velocity."""
    required_components = [Transform, Velocity, PlayerControlled]

    def process_entity(self, entity: Entity, dt: float) -> None:
        velocity = entity.get(Velocity)
        player = entity.get(PlayerControlled)

        # Get movement from input handler
        move = self.world.game.input.get_movement_vector()
        velocity.vx = move[0] * player.speed
        velocity.vy = move[1] * player.speed


class MovementSystem(System):
    """Applies velocity to position."""
    required_components = [Transform, Velocity]
    priority = -10  # Run after input

    def process_entity(self, entity: Entity, dt: float) -> None:
        transform = entity.get(Transform)
        velocity = entity.get(Velocity)

        # Store previous position for interpolation
        transform.prev_x = transform.x
        transform.prev_y = transform.y

        # Apply velocity
        transform.x += velocity.vx * dt
        transform.y += velocity.vy * dt

        # Wrap around screen
        if transform.x < 0:
            transform.x += 1280
            transform.prev_x = transform.x
        elif transform.x > 1280:
            transform.x -= 1280
            transform.prev_x = transform.x

        if transform.y < 0:
            transform.y += 720
            transform.prev_y = transform.y
        elif transform.y > 720:
            transform.y -= 720
            transform.prev_y = transform.y


class SimpleRenderSystem(RenderSystem):
    """Renders entities using Pygame (not ModernGL for simplicity)."""
    required_components = [Transform, Renderable]

    def __init__(self, surface: pygame.Surface):
        super().__init__()
        self.surface = surface

    def pre_render(self, alpha: float) -> None:
        # Clear with dark background
        self.surface.fill((20, 20, 30))

    def render_entity(self, entity: Entity, alpha: float) -> None:
        transform = entity.get(Transform)
        renderable = entity.get(Renderable)

        # Interpolate position for smooth rendering
        x = transform.prev_x + (transform.x - transform.prev_x) * alpha
        y = transform.prev_y + (transform.y - transform.prev_y) * alpha

        pos = (int(x), int(y))
        size = int(renderable.size)

        if renderable.shape == "circle":
            pygame.draw.circle(self.surface, renderable.color, pos, size)
        else:
            rect = pygame.Rect(pos[0] - size, pos[1] - size, size * 2, size * 2)
            pygame.draw.rect(self.surface, renderable.color, rect)


# ============================================================================
# DEMO SCENE
# ============================================================================

class DemoWorld(World):
    """Extended World that holds reference to game."""
    def __init__(self, game: Game):
        super().__init__(game.event_bus)
        self.game = game


class DemoScene(Scene):
    """Demo scene showing the ECS in action."""

    def on_enter(self) -> None:
        super().on_enter()

        # Create render surface (we'll blit this to the GL context)
        self.render_surface = pygame.Surface(
            (self.game.width, self.game.height)
        )

        # Create world
        self.world = DemoWorld(self.game)

        # Add systems
        self.world.add_system(PlayerInputSystem())
        self.world.add_system(MovementSystem())
        self.world.add_system(SimpleRenderSystem(self.render_surface))

        # Create player entity
        player = self.world.create_entity("Player")
        player.add(Transform(x=640, y=360, prev_x=640, prev_y=360))
        player.add(Velocity())
        player.add(PlayerControlled(speed=250.0))
        player.add(Renderable(color=(100, 200, 255), size=25, shape="circle"))

        # Create some other entities
        for i in range(10):
            npc = self.world.create_entity(f"NPC_{i}")
            angle = (i / 10) * math.pi * 2
            x = 640 + math.cos(angle) * 200
            y = 360 + math.sin(angle) * 200

            npc.add(Transform(x=x, y=y, prev_x=x, prev_y=y))
            npc.add(Velocity(vx=math.cos(angle + 0.5) * 50, vy=math.sin(angle + 0.5) * 50))
            npc.add(Renderable(
                color=(255, 100 + i * 15, 100),
                size=10 + i,
                shape="square" if i % 2 == 0 else "circle"
            ))

        print(f"Created {self.world.entity_count} entities")

    def update(self, dt: float) -> None:
        self.world.update(dt)

        # Check for quit
        if self.game.input.is_action_just_pressed(Action.CANCEL):
            self.game.quit()

        # Toggle debug mode
        if self.game.input.is_action_just_pressed(Action.DEBUG_TOGGLE):
            self.game.debug_mode = not self.game.debug_mode
            print(f"Debug mode: {self.game.debug_mode}")

    def render(self, alpha: float) -> None:
        self.world.render(alpha)

        # Draw instructions
        if pygame.font.get_init():
            font = pygame.font.Font(None, 24)
            texts = [
                f"FPS: {self.game.fps:.1f}",
                "WASD/Arrows: Move player",
                "ESC: Quit",
                "F3: Toggle debug",
                f"Entities: {self.world.entity_count}",
            ]
            for i, text in enumerate(texts):
                surface = font.render(text, True, (200, 200, 200))
                self.render_surface.blit(surface, (10, 10 + i * 20))

        # Blit to OpenGL texture and render
        self._blit_to_screen()

    def _blit_to_screen(self) -> None:
        """Blit Pygame surface to OpenGL."""
        # Get raw pixel data
        data = pygame.image.tostring(self.render_surface, "RGBA", True)

        # Create/update texture
        if not hasattr(self, '_texture'):
            self._texture = self.game.ctx.texture(
                (self.game.width, self.game.height), 4, data
            )
            self._texture.filter = (moderngl.NEAREST, moderngl.NEAREST)

            # Create fullscreen quad
            vertices = [
                -1, -1, 0, 0,
                 1, -1, 1, 0,
                 1,  1, 1, 1,
                -1, -1, 0, 0,
                 1,  1, 1, 1,
                -1,  1, 0, 1,
            ]

            self._program = self.game.ctx.program(
                vertex_shader="""
                    #version 330
                    in vec2 in_pos;
                    in vec2 in_uv;
                    out vec2 uv;
                    void main() {
                        gl_Position = vec4(in_pos, 0.0, 1.0);
                        uv = in_uv;
                    }
                """,
                fragment_shader="""
                    #version 330
                    in vec2 uv;
                    out vec4 color;
                    uniform sampler2D tex;
                    void main() {
                        color = texture(tex, uv);
                    }
                """
            )

            vbo = self.game.ctx.buffer(
                data=bytes([int(v * 127 + 128) if isinstance(v, float) else v
                           for v in vertices])
            )
            # Actually, let's do this properly
            import struct
            vbo = self.game.ctx.buffer(struct.pack('12f', *vertices))
            self._vao = self.game.ctx.vertex_array(
                self._program,
                [(vbo, '2f 2f', 'in_pos', 'in_uv')]
            )
        else:
            self._texture.write(data)

        # Render
        self._texture.use(0)
        self._vao.render()


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 60)
    print("Phase 1 Demo: Core Engine Skeleton")
    print("=" * 60)
    print()

    config = GameConfig(
        title="JRPG Engine - Phase 1 Demo",
        width=1280,
        height=720,
        target_fps=60,
    )

    game = Game(config)
    game.debug_mode = True

    # Push initial scene
    game.scene_manager.push(DemoScene(game))

    print("Starting game loop...")
    print("Controls: WASD/Arrows to move, ESC to quit, F3 for debug")
    print()

    game.run()

    print()
    print("Demo complete!")


if __name__ == "__main__":
    main()
