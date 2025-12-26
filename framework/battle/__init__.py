"""
Battle module - turn-based combat system.

Provides:
- Battle actors (party members, enemies)
- Action execution (attack, skill, item, defend, flee)
- Turn order management
- Win/lose conditions
- Reward calculation
"""

from framework.battle.actor import (
    BattleActor,
    ActorType,
    EnemyData,
    create_battle_actor_from_enemy,
)
from framework.battle.actions import (
    BattleActionExecutor,
    ActionType,
    TargetType,
    ActionResult,
    SkillData,
    ItemData,
)
from framework.battle.system import (
    BattleSystem,
    BattleState,
    CommandMenu,
    BattleCommand,
    BattleRewards,
)

__all__ = [
    # Actor
    "BattleActor",
    "ActorType",
    "EnemyData",
    "create_battle_actor_from_enemy",
    # Actions
    "BattleActionExecutor",
    "ActionType",
    "TargetType",
    "ActionResult",
    "SkillData",
    "ItemData",
    # System
    "BattleSystem",
    "BattleState",
    "CommandMenu",
    "BattleCommand",
    "BattleRewards",
]
