"""
Movement system - handles velocity and collision.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from engine.core import System, World, Entity
from framework.components import Transform, Velocity, Collider

if TYPE_CHECKING:
    from framework.world.map import GameMap


class MovementSystem(System):
    """
    Processes movement for all entities with Transform and Velocity.

    Handles:
    - Applying velocity to position
    - Friction
    - Collision detection with map
    """

    def __init__(self, world: World, game_map: Optional[GameMap] = None):
        super().__init__()
        self._world = world
        self.game_map = game_map
        self.required_components = {Transform, Velocity}

    def set_map(self, game_map: GameMap) -> None:
        """Set the current map for collision."""
        self.game_map = game_map

    def process(self, entity_id: int, dt: float) -> None:
        """Process movement for a single entity."""
        entity = self.world.get_entity(entity_id)
        if not entity:
            return

        transform = entity.get(Transform)
        velocity = entity.get(Velocity)

        if not transform or not velocity:
            return

        # Apply friction
        velocity.apply_friction(dt)

        # Clamp to max speed
        velocity.clamp_speed()

        # Calculate new position
        new_x = transform.x + velocity.vx * dt
        new_y = transform.y + velocity.vy * dt

        # Collision detection
        collider = entity.try_get(Collider)
        if collider and self.game_map and not collider.is_trigger:
            # Separate X and Y collision for sliding
            # Check X movement
            bounds = collider.get_bounds(new_x, transform.y)
            if not self.game_map.get_solid_rect(
                bounds[0], bounds[1],
                bounds[2] - bounds[0], bounds[3] - bounds[1]
            ):
                transform.x = new_x
            else:
                velocity.vx = 0

            # Check Y movement
            bounds = collider.get_bounds(transform.x, new_y)
            if not self.game_map.get_solid_rect(
                bounds[0], bounds[1],
                bounds[2] - bounds[0], bounds[3] - bounds[1]
            ):
                transform.y = new_y
            else:
                velocity.vy = 0
        else:
            # No collision, just move
            transform.x = new_x
            transform.y = new_y

    def update(self, dt: float) -> None:
        """Update all entities with movement."""
        entities = self.world.get_entities_with(
            Transform, Velocity
        )
        for entity in entities:
            self.process(entity.id, dt)

    def process_entity(self, entity: Entity, dt: float) -> None:
        """Process a single entity (required by System)."""
        self.process(entity.id, dt)
