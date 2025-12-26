# JRPG Engine Suite - Codebase Guide

## For Code Review Agents

This document provides an overview of the codebase for verification purposes.

## Quick Verification

```bash
python verify_codebase.py
```

This runs ~100 tests checking file structure, imports, and basic functionality.

## Dependencies

```
pygame>=2.0
moderngl>=5.0
imgui-bundle>=1.0
numpy>=1.20
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        GAME LAYER                           │
│  (Your actual game - scenes, entities, game-specific logic) │
├─────────────────────────────────────────────────────────────┤
│                    FRAMEWORK LAYER                          │
│  (JRPG systems: battle, dialog, quests, inventory, etc.)    │
├─────────────────────────────────────────────────────────────┤
│                     ENGINE LAYER                            │
│  (Core: ECS, events, input | Graphics: GPU rendering)       │
├─────────────────────────────────────────────────────────────┤
│                   EXTERNAL LIBS                             │
│  (Pygame, ModernGL, ImGui, NumPy)                          │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
py4py/
├── engine/                 # Core engine (reusable)
│   ├── core/              # ECS, events, game loop
│   │   ├── game.py        # Main game loop, config
│   │   ├── scene.py       # Scene stack management
│   │   ├── entity.py      # Entity container
│   │   ├── component.py   # Component base class
│   │   ├── system.py      # System base class
│   │   ├── world.py       # Entity/component container
│   │   ├── events.py      # Typed event bus
│   │   └── actions.py     # Input action definitions
│   ├── graphics/          # GPU rendering
│   │   ├── context.py     # ModernGL wrapper
│   │   ├── texture.py     # Texture/atlas management
│   │   ├── batch.py       # Sprite batching
│   │   ├── tilemap.py     # Tilemap renderer
│   │   ├── camera.py      # Camera system
│   │   ├── lighting.py    # Dynamic lighting
│   │   ├── particles.py   # Particle system
│   │   └── postfx.py      # Post-processing
│   └── input/
│       └── handler.py     # Action-based input
│
├── framework/             # JRPG-specific systems
│   ├── components/        # Data-only components
│   │   ├── transform.py   # Position, velocity
│   │   ├── physics.py     # Colliders
│   │   ├── character.py   # Stats, HP, MP, EXP
│   │   ├── combat.py      # Battle stats, status effects
│   │   ├── inventory.py   # Items, equipment
│   │   ├── dialog.py      # Dialog state
│   │   ├── ai.py          # AI behavior
│   │   └── interaction.py # Interactables, triggers
│   ├── systems/           # Logic processors
│   │   ├── movement.py    # Movement + collision
│   │   ├── collision.py   # Entity vs entity
│   │   ├── ai.py          # NPC behaviors
│   │   └── interaction.py # Player interactions
│   ├── world/             # Map and entities
│   │   ├── map.py         # Tiled JSON loader
│   │   ├── player.py      # Player factory
│   │   └── npc.py         # NPC factory
│   ├── dialog/            # Conversation system
│   │   ├── system.py      # Dialog manager
│   │   └── parser.py      # Script parser
│   ├── battle/            # Turn-based combat
│   │   ├── actor.py       # Battle participants
│   │   ├── actions.py     # Attack, skill, item
│   │   └── system.py      # Battle controller
│   ├── progression/       # RPG progression
│   │   ├── skills.py      # Skill trees
│   │   └── quests.py      # Quest tracking
│   ├── inventory/         # Item system
│   │   └── items.py       # Item database
│   └── save/              # Persistence
│       └── manager.py     # Save/load
│
├── editor/                # Development tools
│   ├── app.py             # Editor application
│   ├── imgui_backend.py   # ImGui renderer
│   └── panels/            # Editor panels
│       ├── base.py        # Panel base class
│       ├── scene_view.py  # World viewport
│       ├── map_editor.py  # Tile editing
│       ├── asset_browser.py
│       └── properties.py
│
├── demos/                 # Demo applications
│   ├── phase1_demo.py     # Core ECS demo
│   ├── phase2_demo.py     # Graphics demo
│   ├── phase3_demo.py     # Editor demo
│   └── phase4_demo.py     # Full JRPG demo
│
├── poc/                   # Proof of concept
│   └── main.py            # Pygame+ModernGL test
│
├── verify_codebase.py     # THIS FILE - verification
└── CODEBASE_GUIDE.md      # This documentation
```

## Key Design Patterns

### 1. Data-Only Components
Components contain only data (Pydantic/dataclass style). No methods with game logic.

```python
@dataclass
class Health(Component):
    current: int = 100
    max_hp: int = 100
    # Methods are for data manipulation only, not game logic
```

### 2. Logic-Only Systems
Systems contain all game logic. They process entities with specific components.

```python
class MovementSystem(System):
    def update(self, dt: float):
        for entity_id in self.world.get_entities_with_components(Transform, Velocity):
            # Process movement logic here
```

### 3. Typed Events
Events use Enums, not magic strings. Prevents typos and enables autocomplete.

```python
class EngineEvent(Enum):
    ENTITY_CREATED = auto()
    SCENE_TRANSITION = auto()
    # ...
```

### 4. Action-Based Input
Game logic uses abstract actions, not raw keys. Supports rebinding.

```python
class Action(Enum):
    CONFIRM = auto()
    CANCEL = auto()
    MOVE_UP = auto()
    # ...
```

## File Counts by Phase

| Phase | Files | Purpose |
|-------|-------|---------|
| Phase 1: Core | ~10 | ECS, events, input |
| Phase 2: Graphics | ~10 | GPU rendering |
| Phase 3: Editor | ~8 | ImGui tools |
| Phase 4: Framework | ~20 | JRPG systems |
| **Total** | **~48** | Complete suite |

## How to Verify

1. **Run verification script:**
   ```bash
   python verify_codebase.py
   ```

2. **Check all tests pass** - should see "All verification tests passed!"

3. **Run demos** (requires display):
   ```bash
   python demos/phase1_demo.py  # Core ECS
   python demos/phase2_demo.py  # Graphics
   python demos/phase3_demo.py  # Editor
   python demos/phase4_demo.py  # Full JRPG
   ```

## Common Issues

1. **Import errors** - Missing dependencies. Run: `pip install pygame moderngl imgui-bundle numpy`

2. **ModernGL context errors** - Need OpenGL 3.3+ support. Check GPU drivers.

3. **ImGui errors** - Ensure imgui-bundle is installed, not just pyimgui.

## Code Quality Checklist

- [ ] All files exist (verify_codebase checks this)
- [ ] All modules import without errors
- [ ] Components are data-only (no game logic methods)
- [ ] Systems contain logic, components contain data
- [ ] Events use typed Enums
- [ ] Input uses Action enum, not raw keys
- [ ] No circular imports
- [ ] Type hints present on public APIs
