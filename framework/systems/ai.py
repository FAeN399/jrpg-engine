"""
AI system - processes NPC behavior.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import random

from engine.core import System, World, Entity
from framework.components import (
    Transform,
    Velocity,
    Direction,
    AIController,
    AIBehavior,
    AIState,
    PatrolPath,
)

if TYPE_CHECKING:
    from framework.world.map import GameMap


class AISystem(System):
    """
    Processes AI behavior for NPCs and enemies.

    Handles:
    - Idle behavior
    - Patrol paths
    - Chasing targets
    - Returning home
    """

    def __init__(self, world: World, game_map: Optional[GameMap] = None):
        super().__init__(world)
        self.game_map = game_map
        self.required_components = {Transform, AIController}
        self._player_entity: Optional[Entity] = None

    def set_map(self, game_map: GameMap) -> None:
        """Set the current map."""
        self.game_map = game_map

    def set_player(self, player: Entity) -> None:
        """Set the player entity for targeting."""
        self._player_entity = player

    def update(self, dt: float) -> None:
        """Update all AI entities."""
        entities = self.world.get_entities_with_components(
            Transform, AIController
        )
        for entity_id in entities:
            self._process_entity(entity_id, dt)

    def _process_entity(self, entity_id: int, dt: float) -> None:
        """Process AI for a single entity."""
        entity = self.world.get_entity(entity_id)
        if not entity:
            return

        transform = entity.get(Transform)
        ai = entity.get(AIController)
        velocity = entity.get(Velocity)

        if not transform or not ai:
            return

        # Check if we should think
        if not ai.should_think(dt):
            return

        # Process based on behavior type
        if ai.behavior == AIBehavior.STATIC:
            self._process_static(entity, ai)
        elif ai.behavior == AIBehavior.WANDER:
            self._process_wander(entity, transform, velocity, ai)
        elif ai.behavior == AIBehavior.PATROL:
            self._process_patrol(entity, transform, velocity, ai, dt)
        elif ai.behavior == AIBehavior.GUARD:
            self._process_guard(entity, transform, velocity, ai)
        elif ai.behavior == AIBehavior.AGGRESSIVE:
            self._process_aggressive(entity, transform, velocity, ai)
        elif ai.behavior == AIBehavior.COWARD:
            self._process_coward(entity, transform, velocity, ai)

    def _process_static(self, entity: Entity, ai: AIController) -> None:
        """Process static AI (no movement)."""
        ai.state = AIState.IDLE

    def _process_wander(
        self,
        entity: Entity,
        transform: Transform,
        velocity: Optional[Velocity],
        ai: AIController,
    ) -> None:
        """Process wandering AI."""
        if not velocity:
            return

        if ai.state == AIState.IDLE:
            # Randomly start moving
            if random.random() < 0.3:
                ai.state = AIState.PATROL
                # Pick random direction
                dx = random.uniform(-1, 1)
                dy = random.uniform(-1, 1)
                length = (dx * dx + dy * dy) ** 0.5
                if length > 0:
                    velocity.vx = (dx / length) * ai.move_speed
                    velocity.vy = (dy / length) * ai.move_speed
                    transform.facing = Direction.from_vector(dx, dy)
        else:
            # Check if far from home
            dist_home = ((transform.x - ai.home_x) ** 2 +
                        (transform.y - ai.home_y) ** 2) ** 0.5

            if dist_home > ai.chase_range:
                # Return home
                ai.state = AIState.RETURN
                self._move_towards(transform, velocity, ai.home_x, ai.home_y, ai.move_speed)
            elif random.random() < 0.2:
                # Stop moving
                ai.state = AIState.IDLE
                velocity.vx = 0
                velocity.vy = 0

    def _process_patrol(
        self,
        entity: Entity,
        transform: Transform,
        velocity: Optional[Velocity],
        ai: AIController,
        dt: float,
    ) -> None:
        """Process patrol AI."""
        if not velocity:
            return

        path = entity.get(PatrolPath)
        if not path or not path.points:
            ai.state = AIState.IDLE
            return

        current = path.current_point
        if not current:
            return

        # Check if at current point
        dist = ((transform.x - current.x) ** 2 +
                (transform.y - current.y) ** 2) ** 0.5

        if dist < 4.0:
            # At point, wait
            if path.wait_timer > 0:
                path.wait_timer -= dt
                velocity.vx = 0
                velocity.vy = 0
                ai.state = AIState.IDLE
            else:
                # Move to next point
                path.advance()
                ai.state = AIState.PATROL
        else:
            # Move towards point
            ai.state = AIState.PATROL
            self._move_towards(transform, velocity, current.x, current.y, ai.move_speed)

    def _process_guard(
        self,
        entity: Entity,
        transform: Transform,
        velocity: Optional[Velocity],
        ai: AIController,
    ) -> None:
        """Process guard AI (attack intruders, stay near home)."""
        if not velocity:
            return

        player_dist = self._get_player_distance(transform)

        if player_dist is not None and player_dist < ai.sight_range:
            # Player in sight, chase
            ai.state = AIState.CHASE
            if self._player_entity:
                player_t = self._player_entity.get(Transform)
                if player_t:
                    self._move_towards(
                        transform, velocity,
                        player_t.x, player_t.y,
                        ai.move_speed
                    )
        else:
            # Check if far from home
            dist_home = ((transform.x - ai.home_x) ** 2 +
                        (transform.y - ai.home_y) ** 2) ** 0.5

            if dist_home > 8.0:
                # Return home
                ai.state = AIState.RETURN
                self._move_towards(
                    transform, velocity,
                    ai.home_x, ai.home_y,
                    ai.move_speed
                )
            else:
                # Idle at home
                ai.state = AIState.IDLE
                velocity.vx = 0
                velocity.vy = 0

    def _process_aggressive(
        self,
        entity: Entity,
        transform: Transform,
        velocity: Optional[Velocity],
        ai: AIController,
    ) -> None:
        """Process aggressive AI (seek and attack player)."""
        if not velocity:
            return

        player_dist = self._get_player_distance(transform)

        if player_dist is None:
            ai.state = AIState.IDLE
            velocity.vx = 0
            velocity.vy = 0
            return

        if player_dist < ai.attack_range:
            # In attack range
            ai.state = AIState.ATTACK
            velocity.vx = 0
            velocity.vy = 0
            # TODO: Trigger attack
        elif player_dist < ai.sight_range:
            # Chase player
            ai.state = AIState.CHASE
            if self._player_entity:
                player_t = self._player_entity.get(Transform)
                if player_t:
                    self._move_towards(
                        transform, velocity,
                        player_t.x, player_t.y,
                        ai.move_speed
                    )
        elif player_dist < ai.chase_range and ai.state == AIState.CHASE:
            # Continue chasing
            if self._player_entity:
                player_t = self._player_entity.get(Transform)
                if player_t:
                    self._move_towards(
                        transform, velocity,
                        player_t.x, player_t.y,
                        ai.move_speed
                    )
        else:
            # Return home or idle
            dist_home = ((transform.x - ai.home_x) ** 2 +
                        (transform.y - ai.home_y) ** 2) ** 0.5
            if dist_home > 8.0:
                ai.state = AIState.RETURN
                self._move_towards(
                    transform, velocity,
                    ai.home_x, ai.home_y,
                    ai.move_speed
                )
            else:
                ai.state = AIState.IDLE
                velocity.vx = 0
                velocity.vy = 0

    def _process_coward(
        self,
        entity: Entity,
        transform: Transform,
        velocity: Optional[Velocity],
        ai: AIController,
    ) -> None:
        """Process coward AI (flee from player)."""
        if not velocity:
            return

        player_dist = self._get_player_distance(transform)

        if player_dist is not None and player_dist < ai.sight_range:
            # Flee from player
            ai.state = AIState.FLEE
            if self._player_entity:
                player_t = self._player_entity.get(Transform)
                if player_t:
                    # Move away from player
                    dx = transform.x - player_t.x
                    dy = transform.y - player_t.y
                    length = (dx * dx + dy * dy) ** 0.5
                    if length > 0:
                        velocity.vx = (dx / length) * ai.move_speed
                        velocity.vy = (dy / length) * ai.move_speed
                        transform.facing = Direction.from_vector(dx, dy)
        else:
            ai.state = AIState.IDLE
            velocity.vx = 0
            velocity.vy = 0

    def _get_player_distance(self, transform: Transform) -> Optional[float]:
        """Get distance to player."""
        if not self._player_entity:
            return None

        player_t = self._player_entity.get(Transform)
        if not player_t:
            return None

        dx = player_t.x - transform.x
        dy = player_t.y - transform.y
        return (dx * dx + dy * dy) ** 0.5

    def _move_towards(
        self,
        transform: Transform,
        velocity: Velocity,
        target_x: float,
        target_y: float,
        speed: float,
    ) -> None:
        """Move entity towards a target position."""
        dx = target_x - transform.x
        dy = target_y - transform.y
        length = (dx * dx + dy * dy) ** 0.5

        if length > 0:
            velocity.vx = (dx / length) * speed
            velocity.vy = (dy / length) * speed
            transform.facing = Direction.from_vector(dx, dy)
