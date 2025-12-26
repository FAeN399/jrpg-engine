import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Ensure engine modules can be imported
sys.path.append(os.getcwd())

@pytest.fixture(autouse=True)
def mock_pygame():
    """
    Global mock for pygame to allow headless testing.
    Autoused for all tests to prevent accidental window creation.
    """
    with patch('pygame.init'), \
         patch('pygame.display'), \
         patch('pygame.event'), \
         patch('pygame.time'), \
         patch('pygame.mixer'), \
         patch('pygame.image'), \
         patch('pygame.joystick'), \
         patch('pygame.key'), \
         patch('pygame.mouse'), \
         patch('pygame.Surface'):
        
        # Setup specific mock behaviors if needed
        import pygame
        
        # Setup specific mock behaviors if needed
        import pygame
        pygame.time.get_ticks = MagicMock(return_value=0)
        
        yield

@pytest.fixture
def mock_moderngl():
    """Mock moderngl context for graphics tests."""
    with patch('moderngl.create_context') as mock_create:
        ctx = MagicMock()
        mock_create.return_value = ctx
        yield ctx

@pytest.fixture
def event_bus():
    """Fresh EventBus for each test."""
    from engine.core.events import EventBus
    return EventBus()

@pytest.fixture
def world():
    """Fresh World for each test."""
    from engine.core.world import World
    return World()

@pytest.fixture
def sample_entity(world):
    """Entity with common components (Transform)."""
    from engine.core.entity import Entity
    from framework.components.transform import Transform
    
    entity = Entity()
    entity.add(Transform(x=0, y=0))
    world.add_entity(entity)
    return entity
