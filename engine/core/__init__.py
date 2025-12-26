"""
Core engine module.

Exports:
- Game, GameConfig: Main game class and configuration
- Scene, SceneManager: Scene management
- Entity: Entity container
- Component, register_component: Component base and registration
- System, RenderSystem: System base classes
- World: Entity/system container
- EventBus, Event, EngineEvent: Event system
- Action: Input actions
"""

from engine.core.game import Game, GameConfig
from engine.core.scene import Scene, SceneManager
from engine.core.entity import Entity
from engine.core.component import Component, register_component, get_component_type
from engine.core.system import System, RenderSystem
from engine.core.world import World
from engine.core.events import EventBus, Event, EngineEvent, UIEvent, AudioEvent
from engine.core.actions import Action

__all__ = [
    # Game
    "Game",
    "GameConfig",
    # Scene
    "Scene",
    "SceneManager",
    # ECS
    "Entity",
    "Component",
    "register_component",
    "get_component_type",
    "System",
    "RenderSystem",
    "World",
    # Events
    "EventBus",
    "Event",
    "EngineEvent",
    "UIEvent",
    "AudioEvent",
    # Input
    "Action",
]
