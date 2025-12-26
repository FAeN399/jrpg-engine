"""
JRPG Engine

A flexible game engine for JRPG-style games with modern pixel art aesthetics.

Quick Start:
    from engine.core import Game, GameConfig, Scene

    class MyScene(Scene):
        def update(self, dt: float) -> None:
            pass

        def render(self, alpha: float) -> None:
            pass

    config = GameConfig(title="My Game", width=1280, height=720)
    game = Game(config)
    game.scene_manager.push(MyScene(game))
    game.run()
"""

__version__ = "0.1.0"
__author__ = "Developer"

# Re-export core components for convenience
from engine.core import (
    Game,
    GameConfig,
    Scene,
    SceneManager,
    Entity,
    Component,
    register_component,
    System,
    RenderSystem,
    World,
    EventBus,
    Event,
    EngineEvent,
    Action,
)

from engine.input import InputHandler

__all__ = [
    # Core
    "Game",
    "GameConfig",
    "Scene",
    "SceneManager",
    # ECS
    "Entity",
    "Component",
    "register_component",
    "System",
    "RenderSystem",
    "World",
    # Events
    "EventBus",
    "Event",
    "EngineEvent",
    # Input
    "InputHandler",
    "Action",
]
