"""
Scene management system.

Scenes represent different game states (title screen, gameplay, battle, etc.).
The SceneManager handles a stack of scenes, allowing for:
- Push: Add a new scene on top (e.g., open menu over gameplay)
- Pop: Remove the top scene (e.g., close menu)
- Switch: Replace the current scene entirely
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import pygame

if TYPE_CHECKING:
    from engine.core.game import Game
    from engine.core.world import World


class Scene(ABC):
    """
    Abstract base class for game scenes.

    Each scene represents a distinct game state with its own:
    - Update logic
    - Rendering
    - Event handling
    - Optional World (for entity/component scenes)

    Lifecycle:
        1. __init__: Called when scene is created
        2. on_enter: Called when scene becomes active
        3. update/render: Called each frame while active
        4. on_exit: Called when scene is removed or covered
        5. on_destroy: Called when scene is permanently removed
    """

    def __init__(self, game: Game):
        self.game = game
        self.world: World | None = None
        self._is_active = False
        self._is_transparent = False  # If True, scene below is also rendered
        self._blocks_update = True    # If True, scene below doesn't update

    @property
    def is_active(self) -> bool:
        """Whether this scene is currently the top scene."""
        return self._is_active

    @property
    def is_transparent(self) -> bool:
        """Whether scenes below should also be rendered."""
        return self._is_transparent

    @property
    def blocks_update(self) -> bool:
        """Whether this scene blocks updates to scenes below."""
        return self._blocks_update

    def on_enter(self) -> None:
        """
        Called when scene becomes active (pushed or uncovered).

        Override to initialize scene-specific resources.
        """
        self._is_active = True

    def on_exit(self) -> None:
        """
        Called when scene is deactivated (popped or covered).

        Override to pause or save scene state.
        """
        self._is_active = False

    def on_destroy(self) -> None:
        """
        Called when scene is permanently removed from the stack.

        Override to clean up resources.
        """
        if self.world:
            self.world.clear()

    def on_resize(self, width: int, height: int) -> None:
        """
        Called when the window is resized.

        Override to adjust UI or camera.
        """
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        """
        Update scene logic.

        Args:
            dt: Delta time in seconds (fixed timestep)
        """
        pass

    @abstractmethod
    def render(self, alpha: float) -> None:
        """
        Render the scene.

        Args:
            alpha: Interpolation factor (0-1) for smooth rendering
        """
        pass

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle a pygame event.

        Args:
            event: The pygame event

        Returns:
            True if the event was consumed (don't propagate)
        """
        return False


class SceneManager:
    """
    Manages a stack of scenes.

    The scene on top of the stack is the active scene.
    Supports transparent scenes that render scenes below them.
    """

    def __init__(self, game: Game):
        self.game = game
        self._stack: list[Scene] = []
        self._pending_operations: list[tuple[str, Any]] = []

    @property
    def current(self) -> Scene | None:
        """Get the current (top) scene."""
        return self._stack[-1] if self._stack else None

    @property
    def is_empty(self) -> bool:
        """Check if scene stack is empty."""
        return len(self._stack) == 0

    def push(self, scene: Scene) -> None:
        """
        Push a new scene onto the stack.

        The current scene's on_exit is called (but it stays on stack).
        The new scene's on_enter is called.
        """
        self._pending_operations.append(("push", scene))

    def pop(self) -> None:
        """
        Pop the current scene from the stack.

        The current scene's on_exit and on_destroy are called.
        The new top scene's on_enter is called.
        """
        self._pending_operations.append(("pop", None))

    def switch(self, scene: Scene) -> None:
        """
        Replace the current scene with a new one.

        Equivalent to pop + push, but more efficient.
        """
        self._pending_operations.append(("switch", scene))

    def clear(self) -> None:
        """Clear all scenes from the stack."""
        self._pending_operations.append(("clear", None))

    def update(self, dt: float) -> None:
        """Update scenes that should be updated."""
        # Process pending operations first
        self._process_pending()

        # Update scenes from bottom to top, respecting blocks_update
        update_list = self._get_update_list()
        for scene in update_list:
            scene.update(dt)
            if scene.world:
                scene.world.update(dt)

    def render(self, alpha: float) -> None:
        """Render scenes that should be rendered."""
        # Get list of scenes to render (respecting transparency)
        render_list = self._get_render_list()

        for scene in render_list:
            scene.render(alpha)
            if scene.world:
                scene.world.render(alpha)

    def handle_event(self, event: pygame.event.Event) -> None:
        """Pass event to the current scene."""
        if self.current:
            self.current.handle_event(event)

    def on_resize(self, width: int, height: int) -> None:
        """Notify all scenes of window resize."""
        for scene in self._stack:
            scene.on_resize(width, height)

    def _process_pending(self) -> None:
        """Process pending scene operations."""
        while self._pending_operations:
            op, arg = self._pending_operations.pop(0)

            if op == "push":
                self._do_push(arg)
            elif op == "pop":
                self._do_pop()
            elif op == "switch":
                self._do_switch(arg)
            elif op == "clear":
                self._do_clear()

    def _do_push(self, scene: Scene) -> None:
        """Execute push operation."""
        if self._stack:
            self._stack[-1].on_exit()
        self._stack.append(scene)
        scene.on_enter()

    def _do_pop(self) -> None:
        """Execute pop operation."""
        if self._stack:
            scene = self._stack.pop()
            scene.on_exit()
            scene.on_destroy()

            if self._stack:
                self._stack[-1].on_enter()

    def _do_switch(self, scene: Scene) -> None:
        """Execute switch operation."""
        if self._stack:
            old_scene = self._stack.pop()
            old_scene.on_exit()
            old_scene.on_destroy()

        self._stack.append(scene)
        scene.on_enter()

    def _do_clear(self) -> None:
        """Execute clear operation."""
        while self._stack:
            scene = self._stack.pop()
            scene.on_exit()
            scene.on_destroy()

    def _get_render_list(self) -> list[Scene]:
        """Get list of scenes to render (bottom to top)."""
        if not self._stack:
            return []

        result = []
        # Start from top, go down until we find a non-transparent scene
        for i in range(len(self._stack) - 1, -1, -1):
            result.insert(0, self._stack[i])
            if not self._stack[i].is_transparent:
                break

        return result

    def _get_update_list(self) -> list[Scene]:
        """Get list of scenes to update (bottom to top)."""
        if not self._stack:
            return []

        result = []
        # Start from top, go down until we find a scene that blocks updates
        for i in range(len(self._stack) - 1, -1, -1):
            result.insert(0, self._stack[i])
            if self._stack[i].blocks_update:
                break

        return result
