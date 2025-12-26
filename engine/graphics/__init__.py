"""
Graphics module - GPU rendering pipeline.

Exports:
- GraphicsContext: ModernGL context wrapper
- TextureManager, TextureAtlas, TextureRegion: Texture handling
- SpriteBatch, Sprite: Batched sprite rendering
- TilemapRenderer, Tilemap, TileLayer: Tile-based maps
- Camera, CameraBounds: Camera with follow/shake/zoom
- LightingSystem, PointLight, AmbientLight, DayNightCycle: Lighting
- ParticleSystem, ParticleEmitter, ParticleConfig, ParticlePresets: Particles
- PostProcessingChain, BloomEffect, VignetteEffect: Post-processing
- Animation: AnimationClip, AnimationSet, AnimationController, etc.
"""

from engine.graphics.context import GraphicsContext, create_fullscreen_quad
from engine.graphics.texture import TextureManager, TextureAtlas, TextureRegion
from engine.graphics.batch import SpriteBatch, Sprite
from engine.graphics.tilemap import TilemapRenderer, Tilemap, TileLayer, CollisionLayer
from engine.graphics.camera import Camera, CameraBounds, CameraShake
from engine.graphics.lighting import (
    LightingSystem, PointLight, AmbientLight, DayNightCycle
)
from engine.graphics.particles import (
    ParticleSystem, ParticleEmitter, ParticleConfig, ParticlePresets,
    EmitterShape, BlendMode,
)
from engine.graphics.postfx import (
    PostProcessingChain, PostEffect,
    BloomEffect, VignetteEffect, ColorGradeEffect, FadeEffect,
)
from engine.graphics.animation import (
    LoopMode, AnimationFrame, AnimationClip, AnimationSet, AnimationController,
    create_directional_animations,
)
from engine.graphics.animator import (
    AnimationLoader, AnimationManager, generate_grid_regions,
)

__all__ = [
    # Context
    "GraphicsContext",
    "create_fullscreen_quad",
    # Textures
    "TextureManager",
    "TextureAtlas",
    "TextureRegion",
    # Sprites
    "SpriteBatch",
    "Sprite",
    # Tilemap
    "TilemapRenderer",
    "Tilemap",
    "TileLayer",
    "CollisionLayer",
    # Camera
    "Camera",
    "CameraBounds",
    "CameraShake",
    # Lighting
    "LightingSystem",
    "PointLight",
    "AmbientLight",
    "DayNightCycle",
    # Particles
    "ParticleSystem",
    "ParticleEmitter",
    "ParticleConfig",
    "ParticlePresets",
    "EmitterShape",
    "BlendMode",
    # Post-processing
    "PostProcessingChain",
    "PostEffect",
    "BloomEffect",
    "VignetteEffect",
    "ColorGradeEffect",
    "FadeEffect",
    # Animation
    "LoopMode",
    "AnimationFrame",
    "AnimationClip",
    "AnimationSet",
    "AnimationController",
    "create_directional_animations",
    "AnimationLoader",
    "AnimationManager",
    "generate_grid_regions",
]
