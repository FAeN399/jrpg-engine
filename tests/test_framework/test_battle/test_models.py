import pytest
from framework.components import CharacterStats, Health, CombatStats
from framework.battle.actor import BattleActor, ActorType
from engine.core.entity import Entity

def test_stats_init():
    stats = CharacterStats(strength=10, defense=5, magic=2, agility=5)
    assert stats.strength == 10
    
    # Check derived stats if any (e.g. get_attack_power)
    assert stats.get_attack_power() > 0

def test_battle_actor_init():
    e = Entity()
    stats = CharacterStats(strength=10)
    health = Health(current=100, max_hp=100)
    combat = CombatStats()
    
    actor = BattleActor(
        entity_id=e.id,
        name="Hero",
        actor_type=ActorType.PLAYER,
        stats=stats,
        health=health,
        mana=None,
        combat=combat
    )
    
    assert actor.current_hp == 100
    assert actor.name == "Hero"
    assert actor.is_player_controlled

def test_actor_damage():
    # Setup
    e = Entity()
    stats = CharacterStats(strength=10)
    health = Health(current=100, max_hp=100)
    combat = CombatStats()
    
    actor = BattleActor(
        entity_id=e.id,
        name="Enemy",
        actor_type=ActorType.ENEMY,
        stats=stats,
        health=health,
        mana=None,
        combat=combat
    )
    
    actor.take_damage(20)
    assert actor.current_hp == 80
    assert not actor.health.is_dead
    
    actor.take_damage(80)
    assert actor.current_hp == 0
    assert actor.health.is_dead
    assert not actor.is_alive
