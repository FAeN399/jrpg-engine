"""
Character components - stats, health, experience, classes.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Optional

from pydantic import Field
from dataclasses import dataclass

from engine.core.component import Component, register_component


class CharacterClass(Enum):
    """Character class archetypes."""
    NONE = auto()
    WARRIOR = auto()
    MAGE = auto()
    ROGUE = auto()
    CLERIC = auto()
    RANGER = auto()
    # Add more as needed


@register_component
class CharacterStats(Component):
    """
    Base character statistics.

    These are the permanent stats that define a character.
    Combat modifiers are calculated from these.

    Attributes:
        strength: Physical power, affects attack damage
        defense: Physical resistance, reduces damage taken
        magic: Magical power, affects spell damage
        resistance: Magical resistance
        agility: Speed, affects turn order and evasion
        luck: Affects critical hits, drops, etc.
        level: Current character level
        character_class: Class archetype
    """
    strength: int = 10
    defense: int = 10
    magic: int = 10
    resistance: int = 10
    agility: int = 10
    luck: int = 10
    level: int = 1
    character_class: CharacterClass = CharacterClass.NONE

    def get_attack_power(self) -> int:
        """Calculate base attack power."""
        return self.strength + (self.level * 2)

    def get_defense_power(self) -> int:
        """Calculate base defense power."""
        return self.defense + self.level

    def get_magic_power(self) -> int:
        """Calculate base magic power."""
        return self.magic + (self.level * 2)

    def get_speed(self) -> int:
        """Calculate battle speed for turn order."""
        return self.agility + (self.level // 2)


@register_component
class Health(Component):
    """
    Health points tracking.

    Attributes:
        current: Current HP
        max_hp: Maximum HP
        regen_rate: HP regenerated per second (0 for none)
        is_dead: Cached death state
    """
    current: int = 100
    max_hp: int = 100
    regen_rate: float = 0.0
    is_dead: bool = False

    def model_post_init(self, __context):
        """Ensure current doesn't exceed max."""
        self.current = min(self.current, self.max_hp)
        self.is_dead = self.current <= 0

    @property
    def percent(self) -> float:
        """Get health as percentage (0-1)."""
        if self.max_hp <= 0:
            return 0.0
        return self.current / self.max_hp

    @property
    def is_full(self) -> bool:
        """Check if at full health."""
        return self.current >= self.max_hp

    def take_damage(self, amount: int) -> int:
        """
        Take damage.

        Args:
            amount: Damage to take

        Returns:
            Actual damage dealt
        """
        actual = min(amount, self.current)
        self.current -= actual
        if self.current <= 0:
            self.current = 0
            self.is_dead = True
        return actual

    def heal(self, amount: int) -> int:
        """
        Heal health.

        Args:
            amount: Amount to heal

        Returns:
            Actual amount healed
        """
        old = self.current
        self.current = min(self.current + amount, self.max_hp)
        if self.current > 0:
            self.is_dead = False
        return self.current - old

    def revive(self, percent: float = 1.0) -> None:
        """Revive with percentage of max HP."""
        self.current = int(self.max_hp * percent)
        self.is_dead = False


@register_component
class Mana(Component):
    """
    Mana/MP points tracking.

    Attributes:
        current: Current MP
        max_mp: Maximum MP
        regen_rate: MP regenerated per second
    """
    current: int = 50
    max_mp: int = 50
    regen_rate: float = 1.0

    def model_post_init(self, __context):
        """Ensure current doesn't exceed max."""
        self.current = min(self.current, self.max_mp)

    @property
    def percent(self) -> float:
        """Get mana as percentage (0-1)."""
        if self.max_mp <= 0:
            return 0.0
        return self.current / self.max_mp

    def spend(self, amount: int) -> bool:
        """
        Spend mana.

        Args:
            amount: Amount to spend

        Returns:
            True if successful, False if insufficient mana
        """
        if self.current >= amount:
            self.current -= amount
            return True
        return False

    def restore(self, amount: int) -> int:
        """
        Restore mana.

        Args:
            amount: Amount to restore

        Returns:
            Actual amount restored
        """
        old = self.current
        self.current = min(self.current + amount, self.max_mp)
        return self.current - old


@register_component
class Experience(Component):
    """
    Experience and leveling tracking.

    Attributes:
        current: Current XP
        total: Total XP earned (lifetime)
        level: Current level
        to_next_level: XP needed for next level
    """
    current: int = 0
    total: int = 0
    level: int = 1
    to_next_level: int = 100

    def add_exp(self, amount: int) -> int:
        """
        Add experience points.

        Args:
            amount: XP to add

        Returns:
            Number of levels gained
        """
        self.current += amount
        self.total += amount

        levels_gained = 0
        while self.current >= self.to_next_level:
            self.current -= self.to_next_level
            self.level += 1
            levels_gained += 1
            # Exponential XP curve
            self.to_next_level = self._calc_next_level_xp()

        return levels_gained

    def _calc_next_level_xp(self) -> int:
        """Calculate XP needed for next level."""
        # Simple exponential curve
        return int(100 * (1.5 ** (self.level - 1)))

    @property
    def progress(self) -> float:
        """Get progress to next level (0-1)."""
        if self.to_next_level <= 0:
            return 1.0
        return self.current / self.to_next_level
