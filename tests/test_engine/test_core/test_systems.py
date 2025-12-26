import pytest
from engine.core.system import System
from engine.core.entity import Entity
from engine.core.component import Component

class Position(Component):
    x: float = 0.0

class Velocity(Component):
    vx: float = 0.0

class MovementSystem(System):
    required_components = [Position, Velocity]
    
    def process_entity(self, entity, dt):
        pos = entity.get(Position)
        vel = entity.get(Velocity)
        pos.x += vel.vx * dt

def test_system_processing(world):
    # Entity with required matching components
    e1 = Entity()
    e1.add(Position(x=0))
    e1.add(Velocity(vx=10))
    world.add_entity(e1)
    
    # Entity missing one component
    e2 = Entity()
    e2.add(Position(x=0))
    world.add_entity(e2)
    
    system = MovementSystem()
    world.add_system(system)
    
    # Update for 1 second
    world.update(1.0)
    
    # e1 should have moved
    assert e1.get(Position).x == 10.0
    
    # e2 should not have been processed (no velocity) and thus not crashed or moved
    assert e2.get(Position).x == 0.0

def test_system_add_remove(world):
    system = MovementSystem()
    
    world.add_system(system)
    assert system.world is world
    
    world.remove_system(system)
    with pytest.raises(RuntimeError):
        _ = system.world
