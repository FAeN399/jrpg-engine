"""
Battle actors - participants in combat.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum, auto

from framework.components import (
    CharacterStats,
    Health,
    Mana,
    CombatStats,
    StatusEffect,
    StatusType,
    DamageType,
)


class ActorType(Enum):
    """Type of battle actor."""
    PLAYER = auto()
    PARTY_MEMBER = auto()
    ENEMY = auto()
    BOSS = auto()


@dataclass
class BattleActor:
    """
    A participant in battle.

    Wraps entity components for convenient battle access.
    """
    entity_id: int
    name: str
    actor_type: ActorType

    # Stats reference
    stats: CharacterStats
    health: Health
    mana: Optional[Mana]
    combat: CombatStats

    # Battle state
    is_defending: bool = False
    can_act: bool = True
    turn_gauge: float = 0.0  # For ATB-style systems
    action_points: int = 1

    # Display
    sprite_id: Optional[str] = None
    position_index: int = 0  # Position in formation

    # Skills and items
    skills: list[str] = field(default_factory=list)  # Skill IDs

    @property
    def is_alive(self) -> bool:
        """Check if actor is alive."""
        return not self.health.is_dead

    @property
    def is_player_controlled(self) -> bool:
        """Check if this is a player-controlled actor."""
        return self.actor_type in (ActorType.PLAYER, ActorType.PARTY_MEMBER)

    @property
    def current_hp(self) -> int:
        """Get current HP."""
        return self.health.current

    @property
    def max_hp(self) -> int:
        """Get max HP."""
        return self.health.max_hp

    @property
    def current_mp(self) -> int:
        """Get current MP."""
        return self.mana.current if self.mana else 0

    @property
    def max_mp(self) -> int:
        """Get max MP."""
        return self.mana.max_mp if self.mana else 0

    @property
    def hp_percent(self) -> float:
        """Get HP as percentage."""
        return self.health.percent

    @property
    def mp_percent(self) -> float:
        """Get MP as percentage."""
        return self.mana.percent if self.mana else 0.0

    def get_attack(self) -> int:
        """Get total attack power."""
        return self.stats.get_attack_power() + self.combat.attack_modifier

    def get_defense(self) -> int:
        """Get total defense."""
        return self.stats.get_defense_power() + self.combat.defense_modifier

    def get_magic(self) -> int:
        """Get total magic power."""
        return self.stats.get_magic_power() + self.combat.magic_modifier

    def get_resistance(self) -> int:
        """Get total magic resistance."""
        return self.stats.resistance + self.combat.resistance_modifier

    def get_speed(self) -> int:
        """Get battle speed for turn order."""
        return self.stats.get_speed() + self.combat.speed_modifier

    def take_damage(self, amount: int, damage_type: DamageType = DamageType.PHYSICAL) -> int:
        """
        Take damage.

        Args:
            amount: Base damage amount
            damage_type: Type of damage for resistances

        Returns:
            Actual damage dealt
        """
        # Apply damage type modifier
        modifier = self.combat.get_damage_multiplier(damage_type)
        final_amount = int(amount * modifier)

        # Apply defending reduction
        if self.is_defending:
            final_amount = int(final_amount * 0.5)

        return self.health.take_damage(final_amount)

    def heal(self, amount: int) -> int:
        """Heal HP."""
        return self.health.heal(amount)

    def spend_mp(self, amount: int) -> bool:
        """Spend MP. Returns True if successful."""
        if self.mana:
            return self.mana.spend(amount)
        return False

    def restore_mp(self, amount: int) -> int:
        """Restore MP."""
        if self.mana:
            return self.mana.restore(amount)
        return 0

    def apply_status(self, status: StatusEffect) -> bool:
        """Apply a status effect."""
        return self.combat.add_status(status)

    def has_status(self, status_type: StatusType) -> bool:
        """Check if has a status."""
        return self.combat.has_status(status_type)

    def clear_statuses(self) -> None:
        """Clear all status effects."""
        self.combat.clear_all_status()

    def start_defend(self) -> None:
        """Start defending."""
        self.is_defending = True

    def end_defend(self) -> None:
        """Stop defending."""
        self.is_defending = False

    def start_turn(self) -> None:
        """Called at start of actor's turn."""
        self.action_points = 1
        self.can_act = True

    def end_turn(self) -> None:
        """Called at end of actor's turn."""
        self.end_defend()


@dataclass
class EnemyData:
    """Static data for enemy types."""
    id: str
    name: str

    # Base stats
    hp: int = 50
    mp: int = 0
    strength: int = 10
    defense: int = 10
    magic: int = 10
    resistance: int = 10
    agility: int = 10
    luck: int = 5

    # Combat properties
    exp_reward: int = 10
    gold_reward: int = 5
    skills: list[str] = field(default_factory=list)
    drops: list[tuple[str, float]] = field(default_factory=list)  # (item_id, chance)

    # Resistances
    resistances: dict[DamageType, float] = field(default_factory=dict)
    weaknesses: dict[DamageType, float] = field(default_factory=dict)
    immunities: set[StatusType] = field(default_factory=set)

    # AI
    ai_type: str = "basic"
    ai_params: dict = field(default_factory=dict)

    # Display
    sprite_id: str = ""


def create_battle_actor_from_enemy(
    enemy_data: EnemyData,
    entity_id: int,
    position: int = 0,
) -> BattleActor:
    """Create a BattleActor from enemy data."""
    stats = CharacterStats(
        strength=enemy_data.strength,
        defense=enemy_data.defense,
        magic=enemy_data.magic,
        resistance=enemy_data.resistance,
        agility=enemy_data.agility,
        luck=enemy_data.luck,
        level=1,
    )

    health = Health(current=enemy_data.hp, max_hp=enemy_data.hp)
    mana = Mana(current=enemy_data.mp, max_mp=enemy_data.mp) if enemy_data.mp > 0 else None

    combat = CombatStats(
        resistances=enemy_data.resistances.copy(),
        weaknesses=enemy_data.weaknesses.copy(),
        immunities=enemy_data.immunities.copy(),
    )

    return BattleActor(
        entity_id=entity_id,
        name=enemy_data.name,
        actor_type=ActorType.ENEMY,
        stats=stats,
        health=health,
        mana=mana,
        combat=combat,
        skills=enemy_data.skills.copy(),
        sprite_id=enemy_data.sprite_id,
        position_index=position,
    )
