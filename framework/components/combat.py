"""
Combat components - battle stats, status effects, damage types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from engine.core.component import Component


class DamageType(Enum):
    """Types of damage for resistances/weaknesses."""
    PHYSICAL = auto()
    FIRE = auto()
    ICE = auto()
    LIGHTNING = auto()
    WATER = auto()
    EARTH = auto()
    WIND = auto()
    LIGHT = auto()
    DARK = auto()
    HEALING = auto()  # Negative damage


class StatusType(Enum):
    """Status effect types."""
    NONE = auto()
    # Debuffs
    POISON = auto()
    BURN = auto()
    FREEZE = auto()
    PARALYSIS = auto()
    SLEEP = auto()
    CONFUSION = auto()
    BLIND = auto()
    SILENCE = auto()
    SLOW = auto()
    # Buffs
    REGEN = auto()
    HASTE = auto()
    PROTECT = auto()
    SHELL = auto()
    BERSERK = auto()
    INVISIBLE = auto()


@dataclass
class StatusEffect:
    """
    A single status effect instance.

    Attributes:
        status_type: Type of status
        duration: Remaining duration in turns (or seconds for field)
        potency: Strength of effect (damage per tick, stat modifier, etc.)
        source_id: Entity ID that applied this effect
    """
    status_type: StatusType = StatusType.NONE
    duration: float = 3.0
    potency: int = 10
    source_id: Optional[int] = None

    @property
    def is_debuff(self) -> bool:
        """Check if this is a negative effect."""
        return self.status_type in {
            StatusType.POISON,
            StatusType.BURN,
            StatusType.FREEZE,
            StatusType.PARALYSIS,
            StatusType.SLEEP,
            StatusType.CONFUSION,
            StatusType.BLIND,
            StatusType.SILENCE,
            StatusType.SLOW,
        }

    def tick(self, dt: float) -> bool:
        """
        Update duration.

        Returns:
            True if effect expired
        """
        self.duration -= dt
        return self.duration <= 0


@dataclass
class CombatStats(Component):
    """
    Combat-specific modifiers and state.

    These are temporary modifiers that apply during combat,
    calculated from base stats + equipment + buffs.

    Attributes:
        attack_modifier: Added to attack power
        defense_modifier: Added to defense
        magic_modifier: Added to magic power
        resistance_modifier: Added to magic defense
        speed_modifier: Added to speed
        accuracy: Hit chance modifier (1.0 = 100%)
        evasion: Dodge chance (0.0 = 0%)
        critical_chance: Critical hit chance (0.0-1.0)
        critical_multiplier: Critical damage multiplier
        status_effects: Active status effects
        resistances: Damage type resistances (0.5 = 50% damage)
        weaknesses: Damage type weaknesses (1.5 = 150% damage)
        immunities: Status effect immunities
    """
    attack_modifier: int = 0
    defense_modifier: int = 0
    magic_modifier: int = 0
    resistance_modifier: int = 0
    speed_modifier: int = 0
    accuracy: float = 1.0
    evasion: float = 0.0
    critical_chance: float = 0.05
    critical_multiplier: float = 2.0
    status_effects: list[StatusEffect] = field(default_factory=list)
    resistances: dict[DamageType, float] = field(default_factory=dict)
    weaknesses: dict[DamageType, float] = field(default_factory=dict)
    immunities: set[StatusType] = field(default_factory=set)

    def add_status(self, effect: StatusEffect) -> bool:
        """
        Add a status effect.

        Args:
            effect: Status effect to add

        Returns:
            True if added, False if immune
        """
        if effect.status_type in self.immunities:
            return False

        # Check for existing effect of same type
        for existing in self.status_effects:
            if existing.status_type == effect.status_type:
                # Refresh duration if new effect is stronger
                if effect.potency >= existing.potency:
                    existing.duration = effect.duration
                    existing.potency = effect.potency
                return True

        self.status_effects.append(effect)
        return True

    def remove_status(self, status_type: StatusType) -> bool:
        """Remove a status effect by type."""
        for i, effect in enumerate(self.status_effects):
            if effect.status_type == status_type:
                self.status_effects.pop(i)
                return True
        return False

    def has_status(self, status_type: StatusType) -> bool:
        """Check if has a status effect."""
        return any(e.status_type == status_type for e in self.status_effects)

    def get_damage_multiplier(self, damage_type: DamageType) -> float:
        """Get damage multiplier for a damage type."""
        multiplier = 1.0
        if damage_type in self.resistances:
            multiplier *= self.resistances[damage_type]
        if damage_type in self.weaknesses:
            multiplier *= self.weaknesses[damage_type]
        return multiplier

    def update_effects(self, dt: float) -> list[StatusEffect]:
        """
        Update all status effects.

        Returns:
            List of expired effects
        """
        expired = []
        remaining = []
        for effect in self.status_effects:
            if effect.tick(dt):
                expired.append(effect)
            else:
                remaining.append(effect)
        self.status_effects = remaining
        return expired

    def clear_debuffs(self) -> int:
        """Remove all debuffs. Returns count removed."""
        original_count = len(self.status_effects)
        self.status_effects = [e for e in self.status_effects if not e.is_debuff]
        return original_count - len(self.status_effects)

    def clear_all_status(self) -> None:
        """Remove all status effects."""
        self.status_effects.clear()


@dataclass
class BattleState(Component):
    """
    State for entities participating in battle.

    Attributes:
        is_in_battle: Currently in battle
        is_defending: Chose defend action this turn
        is_acting: Currently taking action
        turn_order: Position in turn order
        action_points: AP for multi-action systems (optional)
        guard_multiplier: Damage reduction when defending
    """
    is_in_battle: bool = False
    is_defending: bool = False
    is_acting: bool = False
    turn_order: int = 0
    action_points: int = 1
    guard_multiplier: float = 0.5
