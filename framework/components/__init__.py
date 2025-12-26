"""
JRPG Components - Data-only component definitions.

All components are Pydantic models containing only data.
Logic lives in Systems, not in components.
"""

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
]
