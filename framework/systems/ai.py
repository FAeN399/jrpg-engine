"""
AI system - processes NPC behavior.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable
from enum import Enum, auto
import random

from engine.core import System, World, Entity
from engine.core.events import EventBus
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


class AIEvent(Enum):
    """AI system events."""
    ENCOUNTER_TRIGGERED = auto()  # entity_id, player_id, encounter_type
    AGGRO_GAINED = auto()         # entity_id, target_id
    AGGRO_LOST = auto()           # entity_id
    STATE_CHANGED = auto()        # entity_id, old_state, new_state


class AISystem(System):
    """
    Processes AI behavior for NPCs and enemies.

    Handles:
    - Idle behavior
    - Patrol paths
    - Chasing targets
    - Returning home
    - Combat encounter triggers
    """

    def __init__(self):
        super().__init__()
        self.event_bus: Optional[EventBus] = None
        self.game_map: Optional[GameMap] = None
        self.required_components = {Transform, AIController}
        self._player_entity: Optional[Entity] = None

        # Encounter tracking
        self._encounter_cooldown: float = 0.0
        self._encounter_cooldown_duration: float = 2.0  # Seconds between encounters
        self._entities_in_attack_range: set[int] = set()

        # Callbacks for encounter handling
        self.on_encounter: Optional[Callable[[int, int, str], None]] = None

    def configure(
        self,
        event_bus: Optional[EventBus] = None,
        game_map: Optional[GameMap] = None,
    ) -> 'AISystem':
        """
        Configure the AI system after creation.

        Args:
            event_bus: EventBus for publishing events
            game_map: Game map for pathfinding/collision

        Returns:
            Self for chaining
        """
        self.event_bus = event_bus
        self.game_map = game_map
        return self

    def set_map(self, game_map: GameMap) -> None:
        """Set the current map."""
        self.game_map = game_map

    def set_player(self, player: Entity) -> None:
        """Set the player entity for targeting."""
        self._player_entity = player

    def update(self, dt: float) -> None:
        """Update all AI entities."""
        # Update encounter cooldown
        if self._encounter_cooldown > 0:
            self._encounter_cooldown -= dt

        entities = self.world.get_entities_with(
            Transform, AIController
        )
        for entity in entities:
            self._process_entity(entity.id, dt)

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

        if player_dist is not None and player_dist < ai.attack_range:
            # In attack range
            ai.state = AIState.ATTACK
            velocity.vx = 0
            velocity.vy = 0

            # Trigger encounter if not already triggered
            if entity.id not in self._entities_in_attack_range:
                self._entities_in_attack_range.add(entity.id)
                self._try_trigger_encounter(entity, "guard")

        elif player_dist is not None and player_dist < ai.sight_range:
            # Player in sight, chase (but not in attack range)
            self._entities_in_attack_range.discard(entity.id)
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
            # Not chasing
            self._entities_in_attack_range.discard(entity.id)

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
            self._entities_in_attack_range.discard(entity.id)
            return

        if player_dist < ai.attack_range:
            # In attack range
            ai.state = AIState.ATTACK
            velocity.vx = 0
            velocity.vy = 0

            # Trigger encounter if not already in range and cooldown expired
            if entity.id not in self._entities_in_attack_range:
                self._entities_in_attack_range.add(entity.id)
                self._try_trigger_encounter(entity, "aggressive")
        elif player_dist < ai.sight_range:
            # Chase player (no longer in attack range)
            self._entities_in_attack_range.discard(entity.id)
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
            # Continue chasing (no longer in attack range)
            self._entities_in_attack_range.discard(entity.id)
            if self._player_entity:
                player_t = self._player_entity.get(Transform)
                if player_t:
                    self._move_towards(
                        transform, velocity,
                        player_t.x, player_t.y,
                        ai.move_speed
                    )
        else:
            # Return home or idle (no longer in attack range)
            self._entities_in_attack_range.discard(entity.id)
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

    # Encounter triggering

    def _try_trigger_encounter(self, entity: Entity, encounter_type: str) -> bool:
        """
        Try to trigger a combat encounter.

        Args:
            entity: The enemy entity initiating the encounter
            encounter_type: Type of encounter (e.g., "aggressive", "guard")

        Returns:
            True if encounter was triggered
        """
        # Check cooldown
        if self._encounter_cooldown > 0:
            return False

        if not self._player_entity:
            return False

        player_id = self._player_entity.id
        entity_id = entity.id

        # Set cooldown
        self._encounter_cooldown = self._encounter_cooldown_duration

        # Call callback if set
        if self.on_encounter:
            try:
                self.on_encounter(entity_id, player_id, encounter_type)
            except Exception as e:
                print(f"Error in encounter callback: {e}")

        # Publish event
        if self.event_bus:
            self.event_bus.publish(
                AIEvent.ENCOUNTER_TRIGGERED,
                entity_id=entity_id,
                player_id=player_id,
                encounter_type=encounter_type,
                entity_name=entity.name,
            )

        print(f"Encounter triggered: {entity.name} ({encounter_type})")
        return True

    def set_encounter_cooldown(self, duration: float) -> None:
        """Set the cooldown duration between encounters."""
        self._encounter_cooldown_duration = max(0.1, duration)

    def clear_encounter_tracking(self) -> None:
        """Clear encounter state (e.g., after battle ends)."""
        self._entities_in_attack_range.clear()
        self._encounter_cooldown = 0.0

    def process_entity(self, entity: Entity, dt: float) -> None:
        """Process a single entity (required by System base class)."""
        self._process_entity(entity.id, dt)
