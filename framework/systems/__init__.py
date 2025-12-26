"""
JRPG Systems - Logic-only processors.

Systems process entities with specific components and
contain all game logic. Components are data-only.
"""

from framework.systems.movement import MovementSystem
from framework.systems.collision import CollisionSystem, CollisionEvent
from framework.systems.ai import AISystem, AIEvent
from framework.systems.interaction import InteractionSystem, InteractionEvent
from framework.systems.animation import AnimationSystem, AnimationEvent
from framework.systems.dialog import DialogSystem, DialogEvent

__all__ = [
    "MovementSystem",
    "CollisionSystem",
    "CollisionEvent",
    "AISystem",
    "AIEvent",
    "InteractionSystem",
    "InteractionEvent",
    "AnimationSystem",
    "AnimationEvent",
    "DialogSystem",
    "DialogEvent",
]
