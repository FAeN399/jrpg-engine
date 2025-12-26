import pytest
from pydantic import ValidationError
from engine.core.entity import Entity
from engine.core.component import Component
from engine.core.world import World

class Position(Component):
    x: float = 0.0
    y: float = 0.0

class Velocity(Component):
    vx: float = 0.0
    vy: float = 0.0

def test_entity_creation():
    e = Entity()
    assert e.id > 0
    assert e.active is True

def test_add_get_component():
    e = Entity()
    p = Position(x=10, y=20)
    e.add(p)
    
    retrieved = e.get(Position)
    assert retrieved is p
    assert retrieved.x == 10
    assert retrieved.y == 20

def test_remove_component():
    e = Entity()
    e.add(Position())
    assert e.has(Position)
    
    e.remove(Position)
    assert not e.has(Position)
    assert e.try_get(Position) is None

def test_component_validation():
    with pytest.raises(ValidationError):
        # Position expects float/int, not string (unless pydantic coerces, which it often does)
        # Let's try something clearly invalid or assume strict mode if configured
        # standard pydantic coerces "10" to 10.0. 
        # Pass a dict instead of float for x
        Position(x={"invalid": "type"}) 

def test_world_entity_management(world):
    e = Entity()
    e.add(Position())
    world.add_entity(e)
    
    assert world.entity_count == 1
    
    # Test query
    results = list(world.get_entities_with(Position))
    assert len(results) == 1
    assert results[0] is e
    
    results_empty = list(world.get_entities_with(Velocity))
    assert len(results_empty) == 0

def test_world_cleanup(world):
    e = Entity()
    world.add_entity(e)
    world.destroy_entity(e)
    
    world.update(0.1) # Should cleanup destroyed entities
    
    assert world.entity_count == 0
