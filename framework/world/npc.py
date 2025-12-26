"""
NPC entity - factory and behaviors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from engine.core import Entity, World
from framework.components import (
    Transform,
    Velocity,
    Direction,
    Collider,
    ColliderType,
    CollisionLayer,
    Health,
    DialogSpeaker,
    AIController,
    AIBehavior,
    AIState,
    PatrolPath,
    Interactable,
    InteractionType,
)

if TYPE_CHECKING:
    pass


def create_npc(
    world: World,
    x: float,
    y: float,
    name: str = "NPC",
    dialog_id: Optional[str] = None,
    portrait_id: Optional[str] = None,
    behavior: AIBehavior = AIBehavior.STATIC,
) -> Entity:
    """
    Factory function to create an NPC entity.

    Args:
        world: World to add NPC to
        x: X position
        y: Y position
        name: NPC display name
        dialog_id: ID of dialog script
        portrait_id: Portrait sprite ID
        behavior: AI behavior type

    Returns:
        The created NPC entity
    """
    npc = world.create_entity()
    npc.name = name
    npc.tags.add("npc")

    # Transform
    npc.add(Transform(
        x=x,
        y=y,
        facing=Direction.DOWN,
    ))

    # Movement (for patrolling/wandering)
    npc.add(Velocity(max_speed=50.0))

    # Collision
    npc.add(Collider(
        collider_type=ColliderType.AABB,
        width=14.0,
        height=14.0,
        offset_y=2.0,
        layer=CollisionLayer.NPC.value,
        mask=CollisionLayer.WALL.value | CollisionLayer.PLAYER.value,
        is_static=behavior == AIBehavior.STATIC,
    ))

    # Dialog speaker
    npc.add(DialogSpeaker(
        name=name,
        portrait_id=portrait_id,
        dialog_id=dialog_id,
    ))

    # Interactable
    if dialog_id:
        npc.add(Interactable(
            interaction_type=InteractionType.TALK,
            prompt_text=f"Talk to {name}",
            requires_facing=True,
        ))

    # AI
    if behavior != AIBehavior.NONE:
        npc.add(AIController(
            behavior=behavior,
            state=AIState.IDLE,
            home_x=x,
            home_y=y,
            move_speed=50.0,
        ))

    return npc


def create_patrol_npc(
    world: World,
    x: float,
    y: float,
    patrol_points: list[tuple[float, float]],
    name: str = "Guard",
    dialog_id: Optional[str] = None,
    loop: bool = True,
    reverse: bool = False,
) -> Entity:
    """
    Create an NPC that patrols between points.

    Args:
        world: World to add NPC to
        x: Starting X position
        y: Starting Y position
        patrol_points: List of (x, y) points to patrol
        name: NPC name
        dialog_id: Dialog script ID
        loop: Whether to loop patrol
        reverse: Whether to reverse at end (ping-pong)

    Returns:
        The created NPC entity
    """
    npc = create_npc(
        world, x, y,
        name=name,
        dialog_id=dialog_id,
        behavior=AIBehavior.PATROL,
    )

    # Add patrol path
    path = PatrolPath(loop=loop, reverse=reverse)
    for px, py in patrol_points:
        path.add_point(px, py, wait_time=2.0)

    npc.add(path)

    return npc


def create_enemy(
    world: World,
    x: float,
    y: float,
    name: str = "Enemy",
    enemy_type: str = "slime",
    hp: int = 50,
    behavior: AIBehavior = AIBehavior.AGGRESSIVE,
    sight_range: float = 128.0,
) -> Entity:
    """
    Create an enemy entity.

    Args:
        world: World to add enemy to
        x: X position
        y: Y position
        name: Enemy display name
        enemy_type: Type ID for data lookup
        hp: Health points
        behavior: AI behavior type
        sight_range: Detection range

    Returns:
        The created enemy entity
    """
    enemy = world.create_entity()
    enemy.name = name
    enemy.tags.add("enemy")
    enemy.tags.add(f"enemy_{enemy_type}")

    # Transform
    enemy.add(Transform(
        x=x,
        y=y,
        facing=Direction.DOWN,
    ))

    # Movement
    enemy.add(Velocity(max_speed=60.0))

    # Collision
    enemy.add(Collider(
        collider_type=ColliderType.AABB,
        width=14.0,
        height=14.0,
        layer=CollisionLayer.ENEMY.value,
        mask=CollisionLayer.WALL.value | CollisionLayer.PLAYER.value,
    ))

    # Health
    enemy.add(Health(current=hp, max_hp=hp))

    # AI
    enemy.add(AIController(
        behavior=behavior,
        state=AIState.IDLE,
        home_x=x,
        home_y=y,
        sight_range=sight_range,
        attack_range=20.0,
        chase_range=sight_range * 2,
        move_speed=60.0,
    ))

    return enemy


def create_shopkeeper(
    world: World,
    x: float,
    y: float,
    name: str = "Merchant",
    shop_id: str = "general_store",
    dialog_id: Optional[str] = None,
    portrait_id: Optional[str] = None,
) -> Entity:
    """
    Create a shopkeeper NPC.

    Args:
        world: World to add NPC to
        x: X position
        y: Y position
        name: Shopkeeper name
        shop_id: ID of shop inventory
        dialog_id: Dialog script ID
        portrait_id: Portrait sprite ID

    Returns:
        The created shopkeeper entity
    """
    npc = create_npc(
        world, x, y,
        name=name,
        dialog_id=dialog_id,
        portrait_id=portrait_id,
        behavior=AIBehavior.STATIC,
    )

    npc.tags.add("shopkeeper")

    # Update interactable
    interact = npc.get(Interactable)
    if interact:
        interact.interaction_type = InteractionType.TALK
        interact.prompt_text = f"Shop at {name}'s"
        interact.data['shop_id'] = shop_id

    return npc


def create_sign(
    world: World,
    x: float,
    y: float,
    text: str,
    name: str = "Sign",
) -> Entity:
    """
    Create a readable sign.

    Args:
        world: World to add sign to
        x: X position
        y: Y position
        text: Text to display when read
        name: Sign name

    Returns:
        The created sign entity
    """
    sign = world.create_entity()
    sign.name = name
    sign.tags.add("sign")
    sign.tags.add("interactable")

    # Transform
    sign.add(Transform(x=x, y=y))

    # Collision (for blocking)
    sign.add(Collider(
        collider_type=ColliderType.AABB,
        width=16.0,
        height=16.0,
        layer=CollisionLayer.WALL.value,
        is_static=True,
    ))

    # Interactable
    sign.add(Interactable(
        interaction_type=InteractionType.READ,
        prompt_text="Read",
        requires_facing=True,
        data={'text': text},
    ))

    return sign
