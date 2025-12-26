# Directory Log: engine/
**Date:** 2025-12-25
**Logger:** AI Log Man Robot

---

## Overview

The `engine/` directory contains the **core game engine** - reusable infrastructure for any game type. Built on Pygame + ModernGL for GPU-accelerated 2D rendering.

**Total Files:** 28 Python files
**Version:** 0.1.0
**Target:** 60 FPS with fixed timestep game loop

---

## File Structure

```
engine/
  __init__.py             # Public API exports (66 lines)

  core/                   # Foundation systems
    __init__.py           # Re-exports
    game.py               # Main Game class (273 lines)
    scene.py              # Scene management
    entity.py             # ECS Entity (237 lines)
    component.py          # Pydantic-based Component
    system.py             # Logic processors
    world.py              # Entity container
    events.py             # EventBus pub/sub (modified)
    actions.py            # Input action definitions

  graphics/               # GPU rendering
    __init__.py
    context.py            # ModernGL setup
    texture.py            # Texture loading/regions
    batch.py              # SpriteBatch for rendering
    camera.py             # 2D camera
    tilemap.py            # Tile rendering
    lighting.py           # Point lights, day/night (296 lines)
    particles.py          # GPU particle system (516 lines)
    postfx.py             # Post-processing effects

  input/                  # Input handling
    __init__.py
    handler.py            # InputHandler (397 lines)

  audio/                  # [IN PROGRESS] Sound system
    __init__.py           # Re-exports (modified)
    manager.py            # AudioManager (new)
    music.py              # MusicPlayer with crossfade (new)
    components.py         # AudioSource, AudioListener (new)
    system.py             # AudioSystem ECS integration (new)

  resources/              # [EMPTY] Asset loading
    __init__.py

  i18n/                   # [EMPTY] Localization
    __init__.py

  utils/                  # [EMPTY] Utilities
    __init__.py
```

---

## Core Components

### core/game.py - Game Class (273 lines)
**Purpose:** Main game loop controller.

**Features:**
- Fixed timestep update loop (deterministic physics)
- Variable render loop (smooth visuals)
- Spiral-of-death prevention (frame time clamping)
- Interpolation alpha for smooth rendering
- Window resize handling
- Pause/resume support

**Game Loop:**
```
while running:
    process_events()
    while accumulator >= timestep:
        fixed_update(timestep)
        accumulator -= timestep
    render(interpolation_alpha)
    tick()
```

**Configuration:**
- `title`, `width`, `height`
- `target_fps` (default 60)
- `fixed_timestep` (default 1/60)
- `max_frame_skip` (default 5)
- `vsync`, `fullscreen`, `resizable`

---

### core/entity.py - Entity Class (237 lines)
**Purpose:** Component container with tags.

**Features:**
- Auto-incrementing unique ID
- Component add/remove/get by type
- Tag system for categorization ("player", "enemy", etc.)
- World notification on component changes
- JSON serialization (`to_dict()`)

**Component Access:**
- `entity.add(component)` - Add component
- `entity.get(ComponentType)` - Get component (raises KeyError)
- `entity.try_get(ComponentType)` - Get or None
- `entity.has(Type1, Type2)` - Check all present
- `entity.has_any(Type1, Type2)` - Check any present

---

### core/events.py - EventBus (Modified)
**Purpose:** Publish/subscribe event system.

**Key Methods:**
- `subscribe(event, callback, weak=True)`
- `unsubscribe(event, callback)`
- `publish(event, **data)` (Note: `emit()` deprecated)

**Note:** Lambda functions cannot be weak-referenced. Use `weak=False` for lambdas.

---

### input/handler.py - InputHandler (397 lines)
**Purpose:** Action-based input abstraction.

**Features:**
- Keyboard, mouse, gamepad support
- Semantic action mapping (not raw keys)
- Rebindable key bindings
- Just pressed/released detection
- Movement vector normalization
- Text input callback system
- Multiple keys per action support

**Actions:**
- `MOVE_*` - Movement (WASD, arrows)
- `MENU_*` - Menu navigation
- `CONFIRM`, `CANCEL` - Interaction
- `ATTACK`, `SKILL`, `ITEM` - Combat
- `PAUSE`, `DEBUG` - System

**Usage:**
```python
if input.is_action_pressed(Action.MOVE_RIGHT):
    player.move_right()

if input.is_action_just_pressed(Action.ATTACK):
    player.attack()

move_vec = input.get_movement_vector()  # Normalized (-1 to 1)
```

---

## Graphics Pipeline

### graphics/lighting.py - LightingSystem (296 lines)
**Purpose:** Dynamic 2D lighting.

**Classes:**
- `PointLight` - Point light with position, radius, color, flicker
- `AmbientLight` - Global ambient color/intensity
- `DayNightCycle` - Time-based ambient interpolation
- `LightingSystem` - Light manager (max 16 lights)

**Day/Night Presets:**
- Midnight (0h): Dark blue, 15%
- Sunrise (6h): Orange/pink, 50%
- Noon (12h): Full white, 100%
- Sunset (19h): Warm orange, 60%
- Dusk (21h): Blue/purple, 25%

---

### graphics/particles.py - ParticleSystem (516 lines)
**Purpose:** GPU-accelerated particle effects.

**Features:**
- Configurable emitter shapes (point, line, circle, rectangle)
- Lifetime, velocity, gravity, drag physics
- Size interpolation (shrink/grow)
- Color interpolation (fade)
- Rotation animation
- Blend modes (normal, additive, multiply)
- Instanced rendering for performance

**Presets:**
- `fire()` - Upward warm particles
- `smoke()` - Rising gray clouds
- `sparkle()` - Falling glitter
- `rain()` - Diagonal streaks
- `dust()` - Floating motes
- `magic()` - Blue/purple swirls

---

## Audio System (New)

### audio/manager.py - AudioManager
**Features:**
- Sound caching (loads once, plays many)
- Category-based volume control (master, music, sfx, voice, ambient)
- Spatial audio (distance attenuation)
- Channel management

### audio/music.py - MusicPlayer
**Features:**
- BGM playback with fade transitions
- Crossfade support (fade-to-new)
- Playlist with shuffle option
- Intro/loop section support

### audio/system.py - AudioSystem
**Features:**
- ECS integration for AudioSource components
- Automatic spatial audio based on listener position
- 3D/2D sound modes

---

## Dependencies

```python
import pygame         # Window, input, audio
import moderngl       # GPU rendering
import numpy as np    # Math, matrices
from pydantic import BaseModel  # Components
```

---

## Architecture Principles

1. **Fixed Timestep**
   - Logic at constant rate (deterministic)
   - Rendering interpolated (smooth)

2. **ECS-Lite**
   - Entities = component containers
   - Components = data only (Pydantic models)
   - Systems = logic only (process entities)

3. **Event-Driven**
   - Loosely coupled via EventBus
   - Systems communicate without direct references

4. **GPU-First Rendering**
   - All rendering through ModernGL
   - Sprite batching for performance
   - Per-pixel lighting via shaders

---

## Potential Issues

### 1. Empty Subdirectories
`resources/`, `i18n/`, `utils/` are placeholders with empty `__init__.py`.

### 2. Audio System Incomplete
- No cache management (memory leak potential)
- No preloading mechanism
- No fade-out on quit

### 3. EventBus API Inconsistency
- Some code uses `emit()`, correct method is `publish()`
- Lambda weak-reference issue documented but could catch developers

### 4. Hardcoded Constants
- MAX_LIGHTS = 16 in LightingSystem
- max_particles = 10000 in ParticleSystem
- These could be configurable

---

## Integration Notes

**Importing:**
```python
from engine import (
    Game, GameConfig, Scene,
    Entity, Component, System,
    World, EventBus, Action, InputHandler
)
```

**Creating a Game:**
```python
config = GameConfig(title="My Game", width=1280, height=720)
game = Game(config)
game.scene_manager.push(MyScene(game))
game.run()
```

---

*End of engine/ log*
