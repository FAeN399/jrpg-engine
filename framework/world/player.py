"""
Player entity - factory and controller.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from engine.core import Entity, World
from engine.core.actions import Action
from framework.components import (
    Transform,
    Velocity,
    Direction,
    Collider,
    ColliderType,
    CollisionLayer,
    Health,
    Mana,
    CharacterStats,
    Experience,
    Inventory,
    Equipment,
    DialogContext,
)

if TYPE_CHECKING:
    from engine.input.handler import InputHandler
    from framework.world.map import GameMap


class PlayerController:
    """
    Handles player input and movement.

    This is a utility class that processes input and updates
    player components. It's not a System because it specifically
    handles the player entity.
    """

    def __init__(self, player: Entity, input_handler: InputHandler):
        self.player = player
        self.input = input_handler
        self.move_speed: float = 100.0
        self.can_move: bool = True
        self.interaction_range: float = 24.0

    def update(self, dt: float, game_map: Optional[GameMap] = None) -> None:
        """Update player from input."""
        if not self.can_move:
            return

        transform = self.player.get(Transform)
        velocity = self.player.get(Velocity)

        if not transform or not velocity:
            return

        # Get movement input
        dx = 0.0
        dy = 0.0

        if self.input.is_action_held(Action.MOVE_UP):
            dy = -1.0
        if self.input.is_action_held(Action.MOVE_DOWN):
            dy = 1.0
        if self.input.is_action_held(Action.MOVE_LEFT):
            dx = -1.0
        if self.input.is_action_held(Action.MOVE_RIGHT):
            dx = 1.0

        # Normalize diagonal movement
        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707

        # Apply velocity
        velocity.vx = dx * self.move_speed
        velocity.vy = dy * self.move_speed

        # Update facing direction
        if dx != 0 or dy != 0:
            transform.facing = Direction.from_vector(dx, dy)

        # Calculate new position
        new_x = transform.x + velocity.vx * dt
        new_y = transform.y + velocity.vy * dt

        # Collision detection
        if game_map:
            collider = self.player.get(Collider)
            if collider:
                # Check horizontal movement
                bounds = collider.get_bounds(new_x, transform.y)
                if not game_map.get_solid_rect(
                    bounds[0], bounds[1],
                    bounds[2] - bounds[0], bounds[3] - bounds[1]
                ):
                    transform.x = new_x

                # Check vertical movement
                bounds = collider.get_bounds(transform.x, new_y)
                if not game_map.get_solid_rect(
                    bounds[0], bounds[1],
                    bounds[2] - bounds[0], bounds[3] - bounds[1]
                ):
                    transform.y = new_y
            else:
                # No collider, just move
                transform.x = new_x
                transform.y = new_y

    def get_interaction_point(self) -> tuple[float, float]:
        """Get the point in front of the player for interaction."""
        transform = self.player.get(Transform)
        if not transform:
            return (0, 0)

        vec = transform.facing.vector
        return (
            transform.x + vec[0] * self.interaction_range,
            transform.y + vec[1] * self.interaction_range,
        )

    def freeze(self) -> None:
        """Stop player movement."""
        self.can_move = False
        velocity = self.player.get(Velocity)
        if velocity:
            velocity.vx = 0
            velocity.vy = 0

    def unfreeze(self) -> None:
        """Allow player movement."""
        self.can_move = True


def create_player(
    world: World,
    x: float = 0.0,
    y: float = 0.0,
    name: str = "Player",
) -> Entity:
    """
    Factory function to create a player entity.

    Args:
        world: World to add player to
        x: Starting X position
        y: Starting Y position
        name: Player name

    Returns:
        The created player entity
    """
    player = world.create_entity()
    player.name = name
    player.tags.add("player")

    # Transform
    player.add(Transform(
        x=x,
        y=y,
        facing=Direction.DOWN,
    ))

    # Movement
    player.add(Velocity(
        max_speed=200.0,
        friction=10.0,
    ))

    # Collision
    player.add(Collider(
        collider_type=ColliderType.AABB,
        width=12.0,
        height=12.0,
        offset_y=4.0,  # Offset so collision is at feet
        layer=CollisionLayer.PLAYER.value,
        mask=CollisionLayer.WALL.value | CollisionLayer.NPC.value,
    ))

    # Stats
    player.add(CharacterStats(
        strength=10,
        defense=10,
        magic=10,
        resistance=10,
        agility=10,
        luck=10,
        level=1,
    ))

    # Health & Mana
    player.add(Health(current=100, max_hp=100))
    player.add(Mana(current=50, max_mp=50))

    # Experience
    player.add(Experience())

    # Inventory
    player.add(Inventory(max_slots=20, gold=100))

    # Equipment
    player.add(Equipment())

    # Dialog context (for receiving dialogs)
    player.add(DialogContext())

    return player


def create_party_member(
    world: World,
    x: float = 0.0,
    y: float = 0.0,
    name: str = "Ally",
    stats: Optional[dict] = None,
) -> Entity:
    """
    Factory function to create a party member.

    Similar to player but without player-specific components.

    Args:
        world: World to add member to
        x: Starting X position
        y: Starting Y position
        name: Character name
        stats: Optional stat overrides

    Returns:
        The created party member entity
    """
    member = world.create_entity()
    member.name = name
    member.tags.add("party_member")

    # Transform
    member.add(Transform(
        x=x,
        y=y,
        facing=Direction.DOWN,
    ))

    # Movement (for following)
    member.add(Velocity(max_speed=200.0))

    # Collision
    member.add(Collider(
        collider_type=ColliderType.AABB,
        width=12.0,
        height=12.0,
        offset_y=4.0,
        layer=CollisionLayer.NPC.value,
        mask=CollisionLayer.WALL.value,
    ))

    # Stats
    base_stats = {
        'strength': 10,
        'defense': 10,
        'magic': 10,
        'resistance': 10,
        'agility': 10,
        'luck': 10,
        'level': 1,
    }
    if stats:
        base_stats.update(stats)

    member.add(CharacterStats(**base_stats))

    # Health & Mana
    member.add(Health(current=100, max_hp=100))
    member.add(Mana(current=50, max_mp=50))

    # Experience
    member.add(Experience())

    # Equipment
    member.add(Equipment())

    return member
