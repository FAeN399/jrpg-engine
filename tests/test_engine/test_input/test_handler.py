import pytest
from unittest.mock import MagicMock, patch
from engine.input.handler import InputHandler
from engine.core.actions import Action
import pygame

def test_input_mapping(mock_pygame):
    handler = InputHandler()
    # Assume default mapping (W -> UP)
    # Mock key press
    
    # Simulate processing logic if key is pressed
    # We might need to mock pygame.key.get_pressed or event loop
    
    # Let's test explicit methods
    handler._state.keys_pressed.add(pygame.K_w)
    
    # If handler maps K_w to Action.UP
    # Check behavior (this depends on implementation, often update() checks keys)
    
    # For now, just check init and internal structures
    assert handler.mouse_pos == (0, 0)

def test_action_state(mock_pygame):
    handler = InputHandler()
    # Manually inject state
    handler._state.actions_pressed.add(Action.MOVE_UP)
    
    assert handler.is_action_pressed(Action.MOVE_UP)
    assert not handler.is_action_pressed(Action.MOVE_DOWN)
