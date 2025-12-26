"""
JRPG Components - Data-only component definitions.

All components are Pydantic models containing only data.
Logic lives in Systems, not in components.
"""

from engine.core.component import register_component

from framework.components.transform import Transform, Velocity, Direction
from framework.components.physics import (
    Collider,
    ColliderType,
    CollisionLayer,
    RigidBody,
    TileCollision,
)
from framework.components.character import (
    CharacterStats,
    Health,
    Mana,
    Experience,
    CharacterClass,
)
from framework.components.combat import (
    CombatStats,
    BattleState,
    StatusEffect,
    StatusType,
    DamageType,
)
from framework.components.inventory import (
    Inventory,
    Equipment,
    EquipmentSlot,
    ItemStack,
    ItemType,
)
from framework.components.dialog import (
    DialogContext,
    DialogSpeaker,
    DialogNode,
    DialogChoice,
    DialogState,
)
from framework.components.ai import (
    AIController,
    AIBehavior,
    AIState,
    PatrolPath,
    PatrolPoint,
    Aggro,
)
from framework.components.interaction import (
    Interactable,
    InteractionType,
    TriggerZone,
    Chest,
    Door,
    SavePoint,
)
from framework.components.animated_sprite import (
    AnimatedSprite,
    Sprite,
    SpriteFlash,
    SpriteLayer,
)

__all__ = [
    # Transform
    "Transform",
    "Velocity",
    "Direction",
    # Physics
    "Collider",
    "ColliderType",
    "CollisionLayer",
    "RigidBody",
    "TileCollision",
    # Character
    "CharacterStats",
    "Health",
    "Mana",
    "Experience",
    "CharacterClass",
    # Combat
    "CombatStats",
    "BattleState",
    "StatusEffect",
    "StatusType",
    "DamageType",
    # Inventory
    "Inventory",
    "Equipment",
    "EquipmentSlot",
    "ItemStack",
    "ItemType",
    # Dialog
    "DialogContext",
    "DialogSpeaker",
    "DialogNode",
    "DialogChoice",
    "DialogState",
    # AI
    "AIController",
    "AIBehavior",
    "AIState",
    "PatrolPath",
    "PatrolPoint",
    "Aggro",
    # Interaction
    "Interactable",
    "InteractionType",
    "TriggerZone",
    "Chest",
    "Door",
    "SavePoint",
    # Sprites
    "AnimatedSprite",
    "Sprite",
    "SpriteFlash",
    "SpriteLayer",
]

# Register all components for deserialization
_components_to_register = [
    # Transform
    Transform, Velocity,
    # Physics
    Collider, RigidBody, TileCollision,
    # Character
    CharacterStats, Health, Mana, Experience,
    # Combat
    CombatStats, BattleState,
    # Inventory
    Inventory, Equipment,
    # Dialog
    DialogContext, DialogSpeaker,
    # AI
    AIController, PatrolPath, Aggro,
    # Interaction
    Interactable, TriggerZone, Chest, Door, SavePoint,
    # Sprites
    AnimatedSprite, Sprite, SpriteFlash,
]

for _comp in _components_to_register:
    register_component(_comp)
