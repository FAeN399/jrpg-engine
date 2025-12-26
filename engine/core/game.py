"""
Core Game class with fixed timestep game loop.

The Game class is the main entry point for the engine. It handles:
- Window creation (Pygame + ModernGL)
- Fixed timestep update loop (deterministic physics)
- Variable render loop (smooth visuals)
- Scene management delegation
- Global resource management
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pygame
import moderngl

from engine.core.scene import SceneManager
from engine.core.events import EventBus
from engine.input.handler import InputHandler

if TYPE_CHECKING:
    from engine.graphics.context import GraphicsContext


class GameConfig:
    """Configuration for the game engine."""

    def __init__(
        self,
        title: str = "JRPG Engine",
        width: int = 1280,
        height: int = 720,
        target_fps: int = 60,
        fixed_timestep: float = 1 / 60,
        max_frame_skip: int = 5,
        vsync: bool = True,
        fullscreen: bool = False,
        resizable: bool = True,
    ):
        self.title = title
        self.width = width
        self.height = height
        self.target_fps = target_fps
        self.fixed_timestep = fixed_timestep
        self.max_frame_skip = max_frame_skip
        self.vsync = vsync
        self.fullscreen = fullscreen
        self.resizable = resizable


class Game:
    """
    Main game engine class.

    Implements a fixed timestep game loop with variable rendering.
    This ensures physics/logic run at a consistent rate while
    rendering as fast as possible.

    Usage:
        config = GameConfig(title="My Game", width=1280, height=720)
        game = Game(config)
        game.scene_manager.push(MyStartScene(game))
        game.run()
    """

    def __init__(self, config: GameConfig | None = None):
        self.config = config or GameConfig()
        self._running = False
        self._paused = False

        # Initialize Pygame
        pygame.init()
        pygame.mixer.init()

        # Set OpenGL attributes
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_PROFILE_MASK,
            pygame.GL_CONTEXT_PROFILE_CORE
        )

        # Create window
        flags = pygame.OPENGL | pygame.DOUBLEBUF
        if self.config.fullscreen:
            flags |= pygame.FULLSCREEN
        if self.config.resizable:
            flags |= pygame.RESIZABLE

        self.screen = pygame.display.set_mode(
            (self.config.width, self.config.height),
            flags
        )
        pygame.display.set_caption(self.config.title)

        # Create ModernGL context
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        # Core systems
        self.event_bus = EventBus()
        self.input = InputHandler(self.event_bus)
        self.scene_manager = SceneManager(self)

        # Timing
        self._clock = pygame.time.Clock()
        self._accumulator = 0.0
        self._current_time = time.perf_counter()
        self._frame_count = 0
        self._fps = 0.0
        self._fps_update_time = 0.0

        # Debug info
        self.debug_mode = False

    @property
    def width(self) -> int:
        """Current window width."""
        return self.screen.get_width()

    @property
    def height(self) -> int:
        """Current window height."""
        return self.screen.get_height()

    @property
    def fps(self) -> float:
        """Current frames per second."""
        return self._fps

    @property
    def delta_time(self) -> float:
        """Time since last frame (for interpolation)."""
        return self._clock.get_time() / 1000.0

    def run(self) -> None:
        """
        Start the main game loop.

        Uses a fixed timestep for updates with variable rendering.
        This ensures deterministic physics while rendering smoothly.
        """
        self._running = True
        self._current_time = time.perf_counter()

        while self._running:
            # Calculate delta time
            new_time = time.perf_counter()
            frame_time = new_time - self._current_time
            self._current_time = new_time

            # Prevent spiral of death
            if frame_time > 0.25:
                frame_time = 0.25

            self._accumulator += frame_time

            # Process events
            self._process_events()

            # Fixed timestep updates
            updates = 0
            while self._accumulator >= self.config.fixed_timestep:
                if not self._paused:
                    self._fixed_update(self.config.fixed_timestep)
                self._accumulator -= self.config.fixed_timestep
                updates += 1

                # Prevent too many updates per frame
                if updates >= self.config.max_frame_skip:
                    self._accumulator = 0
                    break

            # Calculate interpolation alpha for smooth rendering
            alpha = self._accumulator / self.config.fixed_timestep

            # Render
            self._render(alpha)

            # Update FPS counter
            self._update_fps()

            # Cap framerate
            self._clock.tick(self.config.target_fps)

        self._shutdown()

    def quit(self) -> None:
        """Request game shutdown."""
        self._running = False

    def pause(self) -> None:
        """Pause the game (stops fixed updates)."""
        self._paused = True

    def resume(self) -> None:
        """Resume the game."""
        self._paused = False

    def toggle_pause(self) -> None:
        """Toggle pause state."""
        self._paused = not self._paused

    def _process_events(self) -> None:
        """Process Pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            elif event.type == pygame.VIDEORESIZE:
                self._on_resize(event.w, event.h)
            else:
                # Let input handler process the event
                self.input.process_event(event)

                # Let current scene handle the event
                self.scene_manager.handle_event(event)

    def _fixed_update(self, dt: float) -> None:
        """
        Fixed timestep update for physics and game logic.

        Args:
            dt: Fixed delta time (always config.fixed_timestep)
        """
        self.input.update()
        self.scene_manager.update(dt)

    def _render(self, alpha: float) -> None:
        """
        Render the current frame.

        Args:
            alpha: Interpolation factor (0-1) for smooth rendering
        """
        # Clear screen
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)

        # Render current scene
        self.scene_manager.render(alpha)

        # Flip display
        pygame.display.flip()

    def _update_fps(self) -> None:
        """Update FPS counter."""
        self._frame_count += 1
        current = time.perf_counter()

        if current - self._fps_update_time >= 1.0:
            self._fps = self._frame_count / (current - self._fps_update_time)
            self._frame_count = 0
            self._fps_update_time = current

            if self.debug_mode:
                pygame.display.set_caption(
                    f"{self.config.title} | FPS: {self._fps:.1f}"
                )

    def _on_resize(self, width: int, height: int) -> None:
        """Handle window resize."""
        self.ctx.viewport = (0, 0, width, height)
        self.scene_manager.on_resize(width, height)

    def _shutdown(self) -> None:
        """Clean shutdown."""
        self.scene_manager.clear()
        pygame.mixer.quit()
        pygame.quit()
