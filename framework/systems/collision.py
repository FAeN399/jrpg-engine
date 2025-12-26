"""
Collision system - entity vs entity collision detection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable
from dataclasses import dataclass

from engine.core import System, World, Entity
from engine.core.events import EventBus, EngineEvent
from framework.components import Transform, Collider

if TYPE_CHECKING:
    pass


@dataclass
class CollisionEvent:
    """Data for a collision between two entities."""
    entity_a: Entity
    entity_b: Entity
    overlap_x: float
    overlap_y: float


class CollisionSystem(System):
    """
    Detects and resolves collisions between entities.

    Uses spatial partitioning for efficiency with many entities.
    """

    def __init__(self, world: World, events: EventBus):
        super().__init__(world)
        self.events = events
        self.required_components = {Transform, Collider}

        # Collision callbacks by layer pair
        self._callbacks: dict[tuple[int, int], Callable[[CollisionEvent], None]] = {}

        # Spatial grid for broad phase
        self.cell_size = 64
        self._grid: dict[tuple[int, int], set[int]] = {}

    def register_callback(
        self,
        layer_a: int,
        layer_b: int,
        callback: Callable[[CollisionEvent], None]
    ) -> None:
        """Register a callback for collisions between two layers."""
        # Store both orderings
        self._callbacks[(layer_a, layer_b)] = callback
        self._callbacks[(layer_b, layer_a)] = callback

    def update(self, dt: float) -> None:
        """Update collision detection."""
        # Clear spatial grid
        self._grid.clear()

        # Get all collidable entities
        entities = list(self.world.get_entities_with_components(
            Transform, Collider
        ))

        # Insert into spatial grid
        for entity_id in entities:
            entity = self.world.get_entity(entity_id)
            if not entity:
                continue

            transform = entity.get(Transform)
            collider = entity.get(Collider)
            if not transform or not collider:
                continue

            # Get cells this entity occupies
            bounds = collider.get_bounds(transform.x, transform.y)
            min_cell_x = int(bounds[0] // self.cell_size)
            min_cell_y = int(bounds[1] // self.cell_size)
            max_cell_x = int(bounds[2] // self.cell_size)
            max_cell_y = int(bounds[3] // self.cell_size)

            for cy in range(min_cell_y, max_cell_y + 1):
                for cx in range(min_cell_x, max_cell_x + 1):
                    cell = (cx, cy)
                    if cell not in self._grid:
                        self._grid[cell] = set()
                    self._grid[cell].add(entity_id)

        # Check collisions within cells
        checked: set[tuple[int, int]] = set()

        for cell, cell_entities in self._grid.items():
            entity_list = list(cell_entities)

            for i, id_a in enumerate(entity_list):
                for id_b in entity_list[i + 1:]:
                    # Skip already checked pairs
                    pair = (min(id_a, id_b), max(id_a, id_b))
                    if pair in checked:
                        continue
                    checked.add(pair)

                    self._check_collision(id_a, id_b)

    def _check_collision(self, id_a: int, id_b: int) -> None:
        """Check collision between two entities."""
        entity_a = self.world.get_entity(id_a)
        entity_b = self.world.get_entity(id_b)

        if not entity_a or not entity_b:
            return

        transform_a = entity_a.get(Transform)
        transform_b = entity_b.get(Transform)
        collider_a = entity_a.get(Collider)
        collider_b = entity_b.get(Collider)

        if not all([transform_a, transform_b, collider_a, collider_b]):
            return

        # Check layer masks
        if not collider_a.overlaps_layer(collider_b.layer):
            return
        if not collider_b.overlaps_layer(collider_a.layer):
            return

        # Get bounds
        bounds_a = collider_a.get_bounds(transform_a.x, transform_a.y)
        bounds_b = collider_b.get_bounds(transform_b.x, transform_b.y)

        # AABB intersection test
        if (bounds_a[2] <= bounds_b[0] or bounds_a[0] >= bounds_b[2] or
            bounds_a[3] <= bounds_b[1] or bounds_a[1] >= bounds_b[3]):
            return  # No intersection

        # Calculate overlap
        overlap_x = min(bounds_a[2], bounds_b[2]) - max(bounds_a[0], bounds_b[0])
        overlap_y = min(bounds_a[3], bounds_b[3]) - max(bounds_a[1], bounds_b[1])

        # Create collision event
        event = CollisionEvent(
            entity_a=entity_a,
            entity_b=entity_b,
            overlap_x=overlap_x,
            overlap_y=overlap_y,
        )

        # Call registered callbacks
        layer_pair = (collider_a.layer, collider_b.layer)
        if layer_pair in self._callbacks:
            self._callbacks[layer_pair](event)

        # Resolve collision if neither is a trigger
        if not collider_a.is_trigger and not collider_b.is_trigger:
            self._resolve_collision(event)

    def _resolve_collision(self, event: CollisionEvent) -> None:
        """Resolve collision by separating entities."""
        transform_a = event.entity_a.get(Transform)
        transform_b = event.entity_b.get(Transform)
        collider_a = event.entity_a.get(Collider)
        collider_b = event.entity_b.get(Collider)

        if not all([transform_a, transform_b, collider_a, collider_b]):
            return

        # Determine which entity to move
        a_static = collider_a.is_static
        b_static = collider_b.is_static

        if a_static and b_static:
            return  # Neither can move

        # Calculate push direction
        dx = transform_a.x - transform_b.x
        dy = transform_a.y - transform_b.y

        # Separate along the axis of least overlap
        if event.overlap_x < event.overlap_y:
            # Separate horizontally
            push = event.overlap_x * (1 if dx > 0 else -1)
            if a_static:
                transform_b.x -= push
            elif b_static:
                transform_a.x += push
            else:
                transform_a.x += push / 2
                transform_b.x -= push / 2
        else:
            # Separate vertically
            push = event.overlap_y * (1 if dy > 0 else -1)
            if a_static:
                transform_b.y -= push
            elif b_static:
                transform_a.y += push
            else:
                transform_a.y += push / 2
                transform_b.y -= push / 2
