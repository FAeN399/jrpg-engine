"""
Battle actions - attack, skill, item, defend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum, auto
import random

from framework.components import DamageType, StatusEffect, StatusType
from framework.battle.actor import BattleActor


class ActionType(Enum):
    """Types of battle actions."""
    ATTACK = auto()
    SKILL = auto()
    ITEM = auto()
    DEFEND = auto()
    FLEE = auto()
    WAIT = auto()


class TargetType(Enum):
    """Action targeting types."""
    NONE = auto()
    SINGLE_ENEMY = auto()
    ALL_ENEMIES = auto()
    SINGLE_ALLY = auto()
    ALL_ALLIES = auto()
    SELF = auto()
    ANY_SINGLE = auto()
    ALL = auto()


@dataclass
class ActionResult:
    """Result of executing a battle action."""
    success: bool = True
    damage_dealt: dict[int, int] = field(default_factory=dict)  # actor_id -> damage
    healing_done: dict[int, int] = field(default_factory=dict)
    mp_cost: int = 0
    critical_hits: set[int] = field(default_factory=set)  # actor_ids that got crit
    statuses_applied: dict[int, list[StatusType]] = field(default_factory=dict)
    message: str = ""
    fled: bool = False


@dataclass
class SkillData:
    """Static data for a skill."""
    id: str
    name: str
    description: str = ""

    # Costs
    mp_cost: int = 0
    hp_cost: int = 0

    # Targeting
    target_type: TargetType = TargetType.SINGLE_ENEMY

    # Effects
    damage_type: DamageType = DamageType.PHYSICAL
    power: int = 100  # Percentage of base attack/magic
    is_magical: bool = False
    healing: bool = False

    # Status effects
    status_effect: Optional[StatusType] = None
    status_chance: float = 1.0
    status_duration: float = 3.0
    status_potency: int = 10

    # Modifiers
    hit_count: int = 1
    accuracy_modifier: float = 1.0
    critical_modifier: float = 1.0

    # Animation
    animation_id: str = ""
    sound_id: str = ""


@dataclass
class ItemData:
    """Static data for a usable item."""
    id: str
    name: str
    description: str = ""

    # Targeting
    target_type: TargetType = TargetType.SINGLE_ALLY

    # Effects
    hp_restore: int = 0
    hp_restore_percent: float = 0.0
    mp_restore: int = 0
    mp_restore_percent: float = 0.0

    # Status
    cures_status: set[StatusType] = field(default_factory=set)
    applies_status: Optional[StatusType] = None
    status_duration: float = 3.0

    # Special
    revive: bool = False
    revive_hp_percent: float = 0.5

    # Damage (for offensive items)
    damage: int = 0
    damage_type: DamageType = DamageType.PHYSICAL


class BattleActionExecutor:
    """
    Executes battle actions and calculates results.
    """

    def __init__(self):
        self._skill_database: dict[str, SkillData] = {}
        self._item_database: dict[str, ItemData] = {}

    def register_skill(self, skill: SkillData) -> None:
        """Register a skill."""
        self._skill_database[skill.id] = skill

    def register_item(self, item: ItemData) -> None:
        """Register an item."""
        self._item_database[item.id] = item

    def execute_attack(
        self,
        attacker: BattleActor,
        targets: list[BattleActor],
    ) -> ActionResult:
        """Execute a basic attack."""
        result = ActionResult()

        for target in targets:
            if not target.is_alive:
                continue

            damage, is_crit = self._calculate_physical_damage(attacker, target)

            if self._check_hit(attacker, target):
                actual_damage = target.take_damage(damage, DamageType.PHYSICAL)
                result.damage_dealt[target.entity_id] = actual_damage
                if is_crit:
                    result.critical_hits.add(target.entity_id)
            else:
                result.message = "Miss!"

        return result

    def execute_skill(
        self,
        user: BattleActor,
        skill_id: str,
        targets: list[BattleActor],
    ) -> ActionResult:
        """Execute a skill."""
        result = ActionResult()

        skill = self._skill_database.get(skill_id)
        if not skill:
            result.success = False
            result.message = f"Unknown skill: {skill_id}"
            return result

        # Check MP cost
        if skill.mp_cost > 0:
            if not user.spend_mp(skill.mp_cost):
                result.success = False
                result.message = "Not enough MP!"
                return result
            result.mp_cost = skill.mp_cost

        # Execute for each target
        for _ in range(skill.hit_count):
            for target in targets:
                if not target.is_alive and not skill.healing:
                    continue

                if skill.healing:
                    heal_amount = self._calculate_healing(user, skill)
                    actual_heal = target.heal(heal_amount)
                    result.healing_done[target.entity_id] = (
                        result.healing_done.get(target.entity_id, 0) + actual_heal
                    )
                else:
                    # Damage
                    if skill.is_magical:
                        damage, is_crit = self._calculate_magical_damage(
                            user, target, skill
                        )
                    else:
                        damage, is_crit = self._calculate_skill_damage(
                            user, target, skill
                        )

                    if self._check_hit(user, target, skill.accuracy_modifier):
                        actual_damage = target.take_damage(damage, skill.damage_type)
                        result.damage_dealt[target.entity_id] = (
                            result.damage_dealt.get(target.entity_id, 0) + actual_damage
                        )
                        if is_crit:
                            result.critical_hits.add(target.entity_id)

                # Apply status effect
                if skill.status_effect and random.random() < skill.status_chance:
                    effect = StatusEffect(
                        status_type=skill.status_effect,
                        duration=skill.status_duration,
                        potency=skill.status_potency,
                        source_id=user.entity_id,
                    )
                    if target.apply_status(effect):
                        if target.entity_id not in result.statuses_applied:
                            result.statuses_applied[target.entity_id] = []
                        result.statuses_applied[target.entity_id].append(
                            skill.status_effect
                        )

        return result

    def execute_item(
        self,
        user: BattleActor,
        item_id: str,
        targets: list[BattleActor],
    ) -> ActionResult:
        """Execute an item use."""
        result = ActionResult()

        item = self._item_database.get(item_id)
        if not item:
            result.success = False
            result.message = f"Unknown item: {item_id}"
            return result

        for target in targets:
            # Revive
            if item.revive and target.health.is_dead:
                target.health.revive(item.revive_hp_percent)
                result.healing_done[target.entity_id] = target.current_hp

            # HP restore
            if item.hp_restore > 0 or item.hp_restore_percent > 0:
                amount = item.hp_restore
                if item.hp_restore_percent > 0:
                    amount += int(target.max_hp * item.hp_restore_percent)
                actual_heal = target.heal(amount)
                result.healing_done[target.entity_id] = (
                    result.healing_done.get(target.entity_id, 0) + actual_heal
                )

            # MP restore
            if item.mp_restore > 0 or item.mp_restore_percent > 0:
                amount = item.mp_restore
                if item.mp_restore_percent > 0:
                    amount += int(target.max_mp * item.mp_restore_percent)
                target.restore_mp(amount)

            # Cure statuses
            for status in item.cures_status:
                target.combat.remove_status(status)

            # Apply status
            if item.applies_status:
                effect = StatusEffect(
                    status_type=item.applies_status,
                    duration=item.status_duration,
                )
                target.apply_status(effect)

            # Damage
            if item.damage > 0:
                actual_damage = target.take_damage(item.damage, item.damage_type)
                result.damage_dealt[target.entity_id] = actual_damage

        return result

    def execute_defend(self, actor: BattleActor) -> ActionResult:
        """Execute defend action."""
        actor.start_defend()
        return ActionResult(message=f"{actor.name} is defending!")

    def execute_flee(
        self,
        party: list[BattleActor],
        enemies: list[BattleActor],
    ) -> ActionResult:
        """Attempt to flee from battle."""
        result = ActionResult()

        # Calculate flee chance based on average speed
        party_speed = sum(a.get_speed() for a in party if a.is_alive)
        enemy_speed = sum(e.get_speed() for e in enemies if e.is_alive)

        alive_party = sum(1 for a in party if a.is_alive)
        alive_enemies = sum(1 for e in enemies if e.is_alive)

        if alive_party > 0 and alive_enemies > 0:
            party_avg = party_speed / alive_party
            enemy_avg = enemy_speed / alive_enemies
            flee_chance = 0.5 + (party_avg - enemy_avg) * 0.01
            flee_chance = max(0.1, min(0.9, flee_chance))  # Clamp 10%-90%
        else:
            flee_chance = 0.5

        if random.random() < flee_chance:
            result.fled = True
            result.message = "Got away safely!"
        else:
            result.success = False
            result.message = "Couldn't escape!"

        return result

    def _calculate_physical_damage(
        self,
        attacker: BattleActor,
        defender: BattleActor,
    ) -> tuple[int, bool]:
        """Calculate physical damage."""
        attack = attacker.get_attack()
        defense = defender.get_defense()

        # Base damage formula
        base_damage = max(1, attack - defense // 2)

        # Random variance (90-110%)
        variance = random.uniform(0.9, 1.1)
        damage = int(base_damage * variance)

        # Critical hit
        is_crit = random.random() < attacker.combat.critical_chance
        if is_crit:
            damage = int(damage * attacker.combat.critical_multiplier)

        return max(1, damage), is_crit

    def _calculate_magical_damage(
        self,
        attacker: BattleActor,
        defender: BattleActor,
        skill: SkillData,
    ) -> tuple[int, bool]:
        """Calculate magical damage."""
        magic = attacker.get_magic()
        resistance = defender.get_resistance()

        # Base damage from skill power
        base_damage = int(magic * skill.power / 100)
        base_damage = max(1, base_damage - resistance // 2)

        # Variance
        variance = random.uniform(0.9, 1.1)
        damage = int(base_damage * variance)

        # Critical
        crit_chance = attacker.combat.critical_chance * skill.critical_modifier
        is_crit = random.random() < crit_chance
        if is_crit:
            damage = int(damage * attacker.combat.critical_multiplier)

        return max(1, damage), is_crit

    def _calculate_skill_damage(
        self,
        attacker: BattleActor,
        defender: BattleActor,
        skill: SkillData,
    ) -> tuple[int, bool]:
        """Calculate physical skill damage."""
        attack = attacker.get_attack()
        defense = defender.get_defense()

        # Base damage from skill power
        base_damage = int(attack * skill.power / 100)
        base_damage = max(1, base_damage - defense // 2)

        # Variance
        variance = random.uniform(0.9, 1.1)
        damage = int(base_damage * variance)

        # Critical
        crit_chance = attacker.combat.critical_chance * skill.critical_modifier
        is_crit = random.random() < crit_chance
        if is_crit:
            damage = int(damage * attacker.combat.critical_multiplier)

        return max(1, damage), is_crit

    def _calculate_healing(
        self,
        healer: BattleActor,
        skill: SkillData,
    ) -> int:
        """Calculate healing amount."""
        magic = healer.get_magic()
        base_heal = int(magic * skill.power / 100)
        variance = random.uniform(0.9, 1.1)
        return max(1, int(base_heal * variance))

    def _check_hit(
        self,
        attacker: BattleActor,
        defender: BattleActor,
        accuracy_mod: float = 1.0,
    ) -> bool:
        """Check if attack hits."""
        hit_chance = attacker.combat.accuracy * accuracy_mod
        evade_chance = defender.combat.evasion

        final_hit = hit_chance * (1 - evade_chance)
        return random.random() < final_hit
