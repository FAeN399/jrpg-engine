"""
JRPG Systems - Logic-only processors.

Systems process entities with specific components and
contain all game logic. Components are data-only.
"""

from framework.systems.movement import MovementSystem
from framework.systems.collision import CollisionSystem, CollisionEvent
from framework.systems.ai import AISystem
from framework.systems.interaction import InteractionSystem, InteractionEvent

__all__ = [
    "MovementSystem",
    "CollisionSystem",
    "CollisionEvent",
    "AISystem",
    "InteractionSystem",
    "InteractionEvent",
]
