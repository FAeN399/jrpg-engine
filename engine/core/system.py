"""
System base class for logic processors.

Systems contain all game logic. They process entities that
have specific component combinations. This separation from
Components (data-only) makes the codebase predictable.

Usage:
    class MovementSystem(System):
        # Define which components this system needs
        required_components = [Transform, Velocity]

        def process_entity(self, entity: Entity, dt: float) -> None:
            transform = entity.get(Transform)
            velocity = entity.get(Velocity)
            transform.x += velocity.vx * dt
            transform.y += velocity.vy * dt
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, Iterator

from engine.core.component import Component

if TYPE_CHECKING:
    from engine.core.entity import Entity
    from engine.core.world import World


class System(ABC):
    """
    Base class for all systems.

    Systems process entities that have specific component combinations.
    They contain all game logic - components are data-only.

    Override required_components to specify which entities to process.
    Override process_entity to define the logic.
    """

    # Components required for this system to process an entity
    required_components: ClassVar[list[type[Component]]] = []

    # Optional components that enhance processing but aren't required
    optional_components: ClassVar[list[type[Component]]] = []

    # Priority for execution order (higher = earlier)
    priority: ClassVar[int] = 0

    # Whether this system is enabled
    enabled: bool = True

    def __init__(self):
        self._world: World | None = None

    @property
    def world(self) -> World:
        """Get the world this system belongs to."""
        if self._world is None:
            raise RuntimeError(f"System {self.__class__.__name__} not attached to world")
        return self._world

    def on_add(self, world: World) -> None:
        """
        Called when system is added to a world.

        Override to perform initialization.
        """
        self._world = world

    def on_remove(self) -> None:
        """
        Called when system is removed from a world.

        Override to perform cleanup.
        """
        self._world = None

    def get_entities(self) -> Iterator[Entity]:
        """
        Get entities that match this system's required components.

        Returns:
            Iterator of matching entities
        """
        if not self._world:
            return iter([])

        if not self.required_components:
            # No requirements = all entities
            return iter(self._world.entities)

        return self._world.get_entities_with(*self.required_components)

    def update(self, dt: float) -> None:
        """
        Update this system.

        Default implementation calls process_entity for each matching entity.
        Override for custom behavior (e.g., batch processing).

        Args:
            dt: Delta time in seconds
        """
        if not self.enabled:
            return

        self.pre_update(dt)

        for entity in self.get_entities():
            if entity.active:
                self.process_entity(entity, dt)

        self.post_update(dt)

    def pre_update(self, dt: float) -> None:
        """
        Called before processing entities.

        Override for per-frame initialization.
        """
        pass

    def post_update(self, dt: float) -> None:
        """
        Called after processing entities.

        Override for per-frame finalization.
        """
        pass

    @abstractmethod
    def process_entity(self, entity: Entity, dt: float) -> None:
        """
        Process a single entity.

        Override to implement system logic.

        Args:
            entity: The entity to process
            dt: Delta time in seconds
        """
        pass

    def __repr__(self) -> str:
        required = ", ".join(c.__name__ for c in self.required_components)
        return f"{self.__class__.__name__}(requires=[{required}])"


class RenderSystem(System):
    """
    Base class for render systems.

    Render systems are separate from logic systems and receive
    an interpolation alpha for smooth rendering.
    """

    def update(self, dt: float) -> None:
        """Render systems don't use update - use render instead."""
        pass

    def process_entity(self, entity: Entity, dt: float) -> None:
        """Render systems don't use process_entity - use render_entity instead."""
        pass

    def render(self, alpha: float) -> None:
        """
        Render this system.

        Args:
            alpha: Interpolation factor (0-1)
        """
        if not self.enabled:
            return

        self.pre_render(alpha)

        for entity in self.get_entities():
            if entity.active:
                self.render_entity(entity, alpha)

        self.post_render(alpha)

    def pre_render(self, alpha: float) -> None:
        """Called before rendering entities."""
        pass

    def post_render(self, alpha: float) -> None:
        """Called after rendering entities."""
        pass

    @abstractmethod
    def render_entity(self, entity: Entity, alpha: float) -> None:
        """
        Render a single entity.

        Args:
            entity: The entity to render
            alpha: Interpolation factor
        """
        pass
