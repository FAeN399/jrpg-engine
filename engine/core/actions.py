"""
Input action definitions.

Actions abstract raw input (keys, buttons) into semantic actions.
Game logic should use Actions, not raw keys. This enables:
- Key rebinding
- Multiple input methods (keyboard, gamepad)
- Cleaner game code

Usage:
    # Check if action is pressed
    if input.is_action_pressed(Action.CONFIRM):
        ...

    # Check if action was just pressed this frame
    if input.is_action_just_pressed(Action.JUMP):
        ...
"""

from enum import Enum, auto


class Action(Enum):
    """
    Semantic input actions.

    Add new actions here as needed. Each action can be mapped
    to multiple input sources (keyboard, gamepad, etc.).
    """

    # Menu navigation
    MENU_UP = auto()
    MENU_DOWN = auto()
    MENU_LEFT = auto()
    MENU_RIGHT = auto()
    CONFIRM = auto()
    CANCEL = auto()
    MENU = auto()

    # Movement
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()

    # Actions
    INTERACT = auto()
    ATTACK = auto()
    JUMP = auto()
    RUN = auto()

    # Camera
    CAMERA_UP = auto()
    CAMERA_DOWN = auto()
    CAMERA_LEFT = auto()
    CAMERA_RIGHT = auto()
    CAMERA_ZOOM_IN = auto()
    CAMERA_ZOOM_OUT = auto()

    # Debug
    DEBUG_TOGGLE = auto()
    DEBUG_STEP = auto()

    # System
    PAUSE = auto()
    QUICKSAVE = auto()
    QUICKLOAD = auto()
    SCREENSHOT = auto()


# Default key bindings (can be customized)
import pygame

DEFAULT_KEY_BINDINGS: dict[Action, list[int]] = {
    # Menu
    Action.MENU_UP: [pygame.K_UP, pygame.K_w],
    Action.MENU_DOWN: [pygame.K_DOWN, pygame.K_s],
    Action.MENU_LEFT: [pygame.K_LEFT, pygame.K_a],
    Action.MENU_RIGHT: [pygame.K_RIGHT, pygame.K_d],
    Action.CONFIRM: [pygame.K_RETURN, pygame.K_SPACE, pygame.K_z],
    Action.CANCEL: [pygame.K_ESCAPE, pygame.K_x],
    Action.MENU: [pygame.K_ESCAPE, pygame.K_TAB],

    # Movement
    Action.MOVE_UP: [pygame.K_UP, pygame.K_w],
    Action.MOVE_DOWN: [pygame.K_DOWN, pygame.K_s],
    Action.MOVE_LEFT: [pygame.K_LEFT, pygame.K_a],
    Action.MOVE_RIGHT: [pygame.K_RIGHT, pygame.K_d],

    # Actions
    Action.INTERACT: [pygame.K_RETURN, pygame.K_SPACE, pygame.K_e],
    Action.ATTACK: [pygame.K_z, pygame.K_j],
    Action.JUMP: [pygame.K_SPACE, pygame.K_w, pygame.K_UP],
    Action.RUN: [pygame.K_LSHIFT, pygame.K_RSHIFT],

    # Camera
    Action.CAMERA_UP: [pygame.K_i],
    Action.CAMERA_DOWN: [pygame.K_k],
    Action.CAMERA_LEFT: [pygame.K_j],
    Action.CAMERA_RIGHT: [pygame.K_l],
    Action.CAMERA_ZOOM_IN: [pygame.K_EQUALS, pygame.K_PLUS],
    Action.CAMERA_ZOOM_OUT: [pygame.K_MINUS],

    # Debug
    Action.DEBUG_TOGGLE: [pygame.K_F3],
    Action.DEBUG_STEP: [pygame.K_F10],

    # System
    Action.PAUSE: [pygame.K_p, pygame.K_ESCAPE],
    Action.QUICKSAVE: [pygame.K_F5],
    Action.QUICKLOAD: [pygame.K_F9],
    Action.SCREENSHOT: [pygame.K_F12],
}

# Gamepad button bindings (SDL controller layout)
DEFAULT_GAMEPAD_BINDINGS: dict[Action, list[int]] = {
    Action.CONFIRM: [0],  # A button
    Action.CANCEL: [1],   # B button
    Action.MENU: [7],     # Start
    Action.ATTACK: [2],   # X button
    Action.JUMP: [0],     # A button
    Action.RUN: [4],      # Left bumper
    Action.PAUSE: [7],    # Start
}

# Gamepad axis bindings (axis_index, threshold, action_positive, action_negative)
DEFAULT_GAMEPAD_AXIS_BINDINGS: list[tuple[int, float, Action, Action]] = [
    (0, 0.5, Action.MOVE_RIGHT, Action.MOVE_LEFT),  # Left stick X
    (1, 0.5, Action.MOVE_DOWN, Action.MOVE_UP),     # Left stick Y
    (2, 0.5, Action.CAMERA_RIGHT, Action.CAMERA_LEFT),  # Right stick X
    (3, 0.5, Action.CAMERA_DOWN, Action.CAMERA_UP),     # Right stick Y
]

# D-pad bindings (hat)
DEFAULT_GAMEPAD_HAT_BINDINGS: dict[tuple[int, int], Action] = {
    (0, 1): Action.MENU_UP,
    (0, -1): Action.MENU_DOWN,
    (-1, 0): Action.MENU_LEFT,
    (1, 0): Action.MENU_RIGHT,
}
