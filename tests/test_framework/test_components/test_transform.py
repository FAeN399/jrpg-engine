import pytest
from framework.components.transform import Transform, Direction

def test_transform_movement():
    t = Transform(x=0, y=0)
    t.move(10, 5)
    assert t.x == 10
    assert t.y == 5
    
    t.move_to(50, 50)
    assert t.position == (50, 50)

def test_direction_logic():
    # Right
    assert Direction.from_vector(1, 0) == Direction.RIGHT
    # Up
    assert Direction.from_vector(0, -1) == Direction.UP
    # Diagonal Up-Right
    assert Direction.from_vector(1, -1) == Direction.UP_RIGHT
    
def test_distance():
    t1 = Transform(x=0, y=0)
    t2 = Transform(x=3, y=4)
    assert t1.distance_to(t2) == 5.0
