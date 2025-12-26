# Animation System Analysis
**Date:** 2025-12-25
**Logger:** AI Log Man Robot

---

## Overview

A complete **frame-based sprite animation system** for 2D games. Designed for JRPG-style character animations with directional movement support.

**Files:**
- `engine/graphics/animation.py` (447 lines)
- `engine/graphics/animator.py` (300 lines)
- `framework/components/animated_sprite.py` (184 lines)
- `framework/systems/animation.py` (424 lines)

**Total:** ~1,355 lines

---

## Architecture

```
Engine Layer (Reusable)
├── animation.py          # Core data structures
│   ├── AnimationFrame    # Single frame data
│   ├── AnimationClip     # Sequence of frames
│   ├── AnimationSet      # Collection of clips
│   └── AnimationController  # Playback logic
│
└── animator.py           # Loading & management
    ├── AnimationLoader   # JSON parsing
    └── AnimationManager  # Resource caching

Framework Layer (JRPG-specific)
├── animated_sprite.py    # ECS Components
│   ├── AnimatedSprite    # Main animation component
│   ├── Sprite            # Static sprite
│   └── SpriteFlash       # Flash effect
│
└── animation.py          # ECS System
    └── AnimationSystem   # Processes animations
```

---

## Core Data Structures

### AnimationFrame
```python
@dataclass
class AnimationFrame:
    region_name: str        # Texture region or frame index
    duration: float = 0.1   # Seconds to display
    offset_x: float = 0.0   # Pixel offset (for attack anims)
    offset_y: float = 0.0
    event: str = None       # Event to fire when reached
```

### AnimationClip
```python
@dataclass
class AnimationClip:
    name: str                           # "walk_down", "attack_left"
    frames: List[AnimationFrame]
    loop_mode: LoopMode = LOOP          # ONCE, LOOP, PING_PONG
    speed_multiplier: float = 1.0

    def get_frame_at_time(time) -> (frame, index)
    def total_duration -> float
    def add_frame(...) -> self  # Fluent API
```

### LoopMode
```python
class LoopMode(Enum):
    ONCE = auto()       # Play once, stop on last frame
    LOOP = auto()       # Loop forever
    PING_PONG = auto()  # Forward then backward
```

### AnimationSet
```python
@dataclass
class AnimationSet:
    clips: Dict[str, AnimationClip]
    default_clip: str = "idle"

    def add_clip(clip) -> self
    def get_clip(name) -> Optional[AnimationClip]
    def has_clip(name) -> bool
```

---

## AnimationController

Standalone playback controller (not ECS-based):

```python
class AnimationController:
    # State
    current_clip: AnimationClip
    current_time: float
    playing: bool
    speed: float

    # Callbacks
    on_frame_event: Callable[[str], None]
    on_animation_complete: Callable[[str], None]
    on_loop: Callable[[str], None]

    # Methods
    def play(clip_name, restart=False) -> bool
    def stop()
    def pause()
    def resume()
    def set_frame(index)
    def update(dt)

    # Properties
    current_frame: AnimationFrame
    current_frame_index: int
    progress: float  # 0.0 to 1.0
    is_complete: bool
```

---

## JSON Animation Format

```json
{
    "atlas": "sprites/hero.png",
    "frame_width": 32,
    "frame_height": 32,
    "animations": {
        "idle_down": {
            "frames": [0, 1, 2, 1],
            "frame_duration": 0.2,
            "loop": true
        },
        "walk_down": {
            "frames": [3, 4, 5, 4],
            "frame_duration": 0.1,
            "loop": true
        },
        "attack_down": {
            "frames": [6, 7, 8, 9],
            "frame_duration": 0.08,
            "loop": false,
            "events": {
                "2": "attack_hit"
            }
        }
    }
}
```

**Supported Loop Values:**
- `true` / `false` (boolean)
- `"once"` / `"loop"` / `"ping_pong"` (string)

---

## ECS Components

### AnimatedSprite (Data-only)
```python
class AnimatedSprite(Component):
    # Animation source
    animation_set_name: str = ""

    # Playback state (managed by system)
    current_clip: str = "idle"
    playing: bool = True
    speed: float = 1.0
    current_time: float = 0.0
    current_frame_index: int = 0
    completed: bool = False

    # Rendering properties
    flip_x: bool = False
    flip_y: bool = False
    visible: bool = True
    layer: SpriteLayer = ENTITY
    z_offset: float = 0.0

    # Visual modifiers
    tint: (r, g, b, a)
    alpha: float = 1.0

    # Frame data (set by system)
    texture_region: str
    offset_x: float
    offset_y: float

    # Atlas info
    atlas_name: str
    frame_width: int = 32
    frame_height: int = 32
```

### SpriteLayer (Render Order)
```python
class SpriteLayer(Enum):
    BACKGROUND = auto()  # Behind everything
    FLOOR = auto()       # Floor decorations
    SHADOW = auto()      # Character shadows
    ENTITY = auto()      # Characters, NPCs
    EFFECT = auto()      # Visual effects
    OVERLAY = auto()     # Above everything
```

### SpriteFlash (Temporary Effect)
```python
class SpriteFlash(Component):
    flash_r/g/b: int = 255
    duration: float = 0.1
    elapsed: float = 0.0
    original_tint_r/g/b: int

    @classmethod
    def damage_flash() -> SpriteFlash  # Red
    def heal_flash() -> SpriteFlash    # Green
    def pickup_flash() -> SpriteFlash  # Yellow
```

---

## AnimationSystem (ECS)

```python
class AnimationSystem(System):
    required_components = {AnimatedSprite}

    # Animation management
    def register_animation_set(name, anim_set)
    def load_animation_set(name, path) -> AnimationSet
    def get_animation_set(name) -> AnimationSet
    def create_animation_set(name) -> AnimationSet

    # Entity animation control
    def play(entity_id, clip_name, restart=False) -> bool
    def play_directional(entity_id, base_name, direction=None) -> bool
    def stop(entity_id)
    def pause(entity_id)
    def resume(entity_id)
    def set_speed(entity_id, speed)

    # Flash effects
    def flash(entity_id, r, g, b, duration)
    def damage_flash(entity_id)
    def heal_flash(entity_id)

    # Frame events
    def register_frame_event_handler(event_name, callback)
    def unregister_frame_event_handler(event_name)

    # System update
    def update(dt)  # Processes all animated entities
```

---

## Directional Animation Support

The system automatically selects direction-based animations:

```python
# Example: Walking character
animation_system.play_directional(player_id, "walk")

# Maps Direction enum to animation suffix:
Direction.UP        -> "walk_up"
Direction.DOWN      -> "walk_down"
Direction.LEFT      -> "walk_left"
Direction.RIGHT     -> "walk_right"
Direction.UP_LEFT   -> "walk_left"
Direction.UP_RIGHT  -> "walk_right"
Direction.DOWN_LEFT -> "walk_left"
Direction.DOWN_RIGHT-> "walk_right"
```

Uses `Transform.facing` if no direction specified.

---

## Frame Events

Fire callbacks/events when specific frames are reached:

```python
# In JSON definition
"attack_down": {
    "frames": [6, 7, 8, 9],
    "events": {
        "2": "attack_hit"  # Fire on frame 2
    }
}

# Register handler in code
animation_system.register_frame_event_handler(
    "attack_hit",
    lambda entity_id, clip: deal_damage(entity_id)
)

# Also published to EventBus
AnimationEvent.FRAME_EVENT  # entity_id, clip_name, event_name
```

---

## AnimationEvents (EventBus)

```python
class AnimationEvent(Enum):
    ANIMATION_STARTED = auto()    # clip_name, entity_id
    ANIMATION_COMPLETED = auto()  # clip_name, entity_id (ONCE mode)
    ANIMATION_LOOPED = auto()     # clip_name, entity_id
    FRAME_EVENT = auto()          # event_name, clip_name, entity_id
```

---

## Usage Example

```python
# Setup
anim_system = AnimationSystem(world, event_bus, "game/assets")

# Load animations from JSON
anim_system.load_animation_set("hero", "animations/hero.json")

# Create entity
player = Entity()
player.add(Transform(x=100, y=100))
player.add(AnimatedSprite(
    animation_set_name="hero",
    current_clip="idle_down",
    frame_width=32,
    frame_height=32,
))
world.add_entity(player)

# Play animations
anim_system.play(player.id, "walk_down")
anim_system.play_directional(player.id, "attack")

# Flash on damage
anim_system.damage_flash(player.id)

# In game loop
anim_system.update(dt)
```

---

## Helper Functions

### create_directional_animations()
```python
# Create walk animations for 4 directions
anim_set = create_directional_animations(
    base_name="walk",
    frames_per_direction=4,
    frame_duration=0.1,
    directions=['down', 'left', 'right', 'up']
)
# Creates: walk_down, walk_left, walk_right, walk_up
```

### generate_grid_regions()
```python
# Generate frame regions for sprite sheet
regions = generate_grid_regions(
    atlas_width=256,
    atlas_height=256,
    frame_width=32,
    frame_height=32,
    padding=1,
    margin=0,
)
# Returns: [(0,0,32,32), (33,0,32,32), ...]
```

---

## Quality Assessment

### Strengths
- Clean separation: data structures, loader, ECS integration
- Multiple loop modes (once, loop, ping-pong)
- Frame events for gameplay triggers
- Directional animation support (JRPG essential)
- Flash effects built-in
- JSON loading with caching
- Fluent API for building animations

### Considerations
- No skeletal animation (frame-based only)
- No animation blending/transitions
- No animation state machine
- Frame events by index only (not by time)

---

## Integration

**Depends on:**
- `engine.core.component.Component`
- `engine.core.System`
- `engine.core.World`
- `engine.core.EventBus`
- `framework.components.transform.Transform`

**Used by:**
- Rendering system (reads AnimatedSprite data)
- Battle system (attack animations, damage flash)
- Movement system (direction-based animation)

---

*End of animation system log*
