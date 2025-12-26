import pytest
from engine.core.entity import Entity
from framework.components.transform import Transform, Velocity
from framework.systems.movement import MovementSystem

def test_movement_integration(world):
    e = Entity()
    e.add(Transform(x=0, y=0))
    e.add(Velocity(vx=100, vy=0))
    world.add_entity(e)
    
    sys = MovementSystem(world)
    world.add_system(sys)
    
    # Update 0.5s
    world.update(0.5)
    
    assert e.get(Transform).x == 50.0
    assert e.get(Transform).y == 0.0

def test_friction(world):
    e = Entity()
    e.add(Transform())
    # 100 speed, friction 0.5 (halves speed per sec, simplified)
    # The actual logic might be linear or multiplicative: factor = max(0, 1 - friction * dt)
    e.add(Velocity(vx=100, friction=2.0)) 
    world.add_entity(e)
    
    sys = MovementSystem(world)
    world.add_system(sys)
    
    # Update 0.1s -> factor = 1 - 2.0*0.1 = 0.8
    # New speed = 100 * 0.8 = 80
    world.update(0.1)
    
    vel = e.get(Velocity)
    assert 79.9 < vel.vx < 80.1  # Float tolerance
