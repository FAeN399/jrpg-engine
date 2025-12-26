# Gemini Handoff: JRPG Engine Suite Tasks

## Project Context

You are working on a JRPG game engine suite built in Python. The engine uses:
- **Pygame 2.x** for windowing, input, and audio
- **ModernGL** for GPU rendering (shaders, batching, post-processing)
- **Pydantic** for data validation (components are BaseModel subclasses)
- **ECS-lite architecture**: Components are DATA ONLY, Systems contain LOGIC ONLY
- **Typed Events**: Enum-based event system (not magic strings)

**Project Location**: `D:\py4py`

**Current Status**: 87 Python files, core engine complete, JRPG framework complete, audio system complete (you did this!).

---

# Task 1: Test Suite Generation

## Priority: HIGH

## Overview

The `tests/` directory structure exists but contains only empty `__init__.py` files. Generate a comprehensive pytest test suite covering all 87 Python files.

## Target Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── test_engine/
│   ├── __init__.py
│   ├── test_core/
│   │   ├── test_entity.py
│   │   ├── test_component.py
│   │   ├── test_system.py
│   │   ├── test_world.py
│   │   ├── test_events.py
│   │   ├── test_scene.py
│   │   ├── test_game.py
│   │   └── test_actions.py
│   ├── test_graphics/
│   │   ├── test_context.py
│   │   ├── test_batch.py
│   │   ├── test_camera.py
│   │   ├── test_lighting.py
│   │   ├── test_particles.py
│   │   └── test_postfx.py
│   ├── test_audio/
│   │   ├── test_manager.py
│   │   ├── test_music.py
│   │   └── test_components.py
│   └── test_input/
│       └── test_handler.py
├── test_framework/
│   ├── __init__.py
│   ├── test_components/
│   │   ├── test_transform.py
│   │   ├── test_physics.py
│   │   ├── test_combat.py
│   │   ├── test_inventory.py
│   │   ├── test_character.py
│   │   ├── test_ai.py
│   │   └── test_dialog.py
│   ├── test_systems/
│   │   ├── test_movement.py
│   │   ├── test_collision.py
│   │   └── test_ai_system.py
│   ├── test_battle/
│   │   ├── test_actor.py
│   │   ├── test_actions.py
│   │   └── test_effects.py
│   ├── test_dialog/
│   │   ├── test_parser.py
│   │   └── test_system.py
│   ├── test_inventory/
│   │   └── test_container.py
│   ├── test_progression/
│   │   ├── test_stats.py
│   │   └── test_quests.py
│   └── test_save/
│       └── test_manager.py
└── test_editor/
    └── __init__.py
```

## Requirements

### 1. `tests/conftest.py` - Shared Fixtures

```python
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_pygame():
    """Mock pygame for tests that don't need real display."""
    with patch('pygame.init'), \
         patch('pygame.display.set_mode'), \
         patch('pygame.mixer.init'):
        yield

@pytest.fixture
def event_bus():
    """Fresh EventBus for each test."""
    from engine.core.events import EventBus
    return EventBus()

@pytest.fixture
def world():
    """Fresh World for each test."""
    from engine.core.world import World
    return World()

@pytest.fixture
def sample_entity(world):
    """Entity with common components."""
    from engine.core.entity import Entity
    from framework.components.transform import Transform
    entity = Entity()
    entity.add_component(Transform(x=0, y=0))
    world.add_entity(entity)
    return entity

# Add more fixtures as needed
```

### 2. Test Patterns to Follow

**Component Tests:**
```python
# test_framework/test_components/test_transform.py
import pytest
from framework.components.transform import Transform

class TestTransform:
    def test_default_values(self):
        t = Transform()
        assert t.x == 0.0
        assert t.y == 0.0
        assert t.rotation == 0.0
        assert t.scale_x == 1.0
        assert t.scale_y == 1.0

    def test_custom_values(self):
        t = Transform(x=100, y=200, rotation=45)
        assert t.x == 100
        assert t.y == 200
        assert t.rotation == 45

    def test_position_property(self):
        t = Transform(x=10, y=20)
        assert t.position == (10, 20)

    def test_pydantic_validation(self):
        # Should accept numeric types
        t = Transform(x=10, y=20.5)
        assert isinstance(t.x, float)
```

**System Tests:**
```python
# test_framework/test_systems/test_movement.py
import pytest
from framework.systems.movement import MovementSystem
from framework.components.transform import Transform
from framework.components.physics import Velocity

class TestMovementSystem:
    def test_applies_velocity(self, world, sample_entity):
        sample_entity.add_component(Velocity(vx=10, vy=5))
        system = MovementSystem()
        system.process(world, dt=0.1)

        transform = sample_entity.get_component(Transform)
        assert transform.x == 1.0  # 10 * 0.1
        assert transform.y == 0.5  # 5 * 0.1
```

**Event Tests:**
```python
# test_engine/test_core/test_events.py
import pytest
from engine.core.events import EventBus, EngineEvent

class TestEventBus:
    def test_subscribe_and_publish(self, event_bus):
        received = []
        event_bus.subscribe(EngineEvent.ENTITY_CREATED, lambda d: received.append(d))
        event_bus.publish(EngineEvent.ENTITY_CREATED, {"id": 1})
        assert len(received) == 1
        assert received[0]["id"] == 1

    def test_unsubscribe(self, event_bus):
        received = []
        handler = lambda d: received.append(d)
        event_bus.subscribe(EngineEvent.ENTITY_CREATED, handler)
        event_bus.unsubscribe(EngineEvent.ENTITY_CREATED, handler)
        event_bus.publish(EngineEvent.ENTITY_CREATED, {})
        assert len(received) == 0
```

**Battle System Tests:**
```python
# test_framework/test_battle/test_actions.py
import pytest
from framework.battle.actions import BattleActionExecutor
from framework.battle.actor import BattleActor

class TestBattleActionExecutor:
    def test_damage_calculation(self):
        attacker = BattleActor(name="Hero", attack=50, defense=10)
        defender = BattleActor(name="Slime", attack=10, defense=5, hp=100)

        executor = BattleActionExecutor()
        result = executor.execute_attack(attacker, defender)

        assert result.damage > 0
        assert defender.hp < 100
```

### 3. Testing Strategy

| Module | Mocking Strategy |
|--------|------------------|
| `core/` | No mocking needed (pure Python) |
| `graphics/` | Mock ModernGL context |
| `audio/` | Mock pygame.mixer |
| `input/` | Mock pygame.event |
| `framework/` | Mostly no mocking (data + logic) |

### 4. Edge Cases to Cover

- Empty world processing
- Entity without required components
- Invalid component values (Pydantic validation)
- Event handlers that throw exceptions
- Zero delta time
- Negative values where inappropriate
- Component removal during iteration
- Save/load round-trip consistency

## Files to Read First

```
engine/core/entity.py
engine/core/component.py
engine/core/events.py
engine/core/world.py
framework/components/transform.py
framework/components/combat.py
framework/battle/actions.py
framework/progression/quests.py
verify_codebase.py  # See existing test patterns
```

## Verification

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=engine --cov=framework --cov-report=html

# Expected: 80%+ coverage on core modules
```

---

# Task 2: JSON Schemas & Data Files

## Priority: HIGH

## Overview

Create JSON schemas and sample data files for game content. The framework uses Pydantic models - generate matching JSON structures.

## Target Structure

```
game/data/
├── schemas/                    # JSON Schema definitions
│   ├── item.schema.json
│   ├── enemy.schema.json
│   ├── skill.schema.json
│   ├── quest.schema.json
│   ├── dialog.schema.json
│   └── map.schema.json
├── database/                   # Game data
│   ├── items/
│   │   ├── weapons.json
│   │   ├── armor.json
│   │   ├── consumables.json
│   │   └── key_items.json
│   ├── enemies/
│   │   ├── slimes.json
│   │   ├── undead.json
│   │   ├── beasts.json
│   │   └── bosses.json
│   ├── skills/
│   │   ├── warrior.json
│   │   ├── mage.json
│   │   └── healer.json
│   └── quests/
│       ├── main_story.json
│       └── side_quests.json
└── templates/                  # Empty templates for users
    ├── item_template.json
    ├── enemy_template.json
    └── quest_template.json
```

## Schema Definitions

### 1. Item Schema (`schemas/item.schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Item",
  "type": "object",
  "required": ["id", "name", "type"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9_]*$",
      "description": "Unique identifier (snake_case)"
    },
    "name": {
      "type": "string",
      "description": "Display name"
    },
    "description": {
      "type": "string",
      "default": ""
    },
    "type": {
      "type": "string",
      "enum": ["weapon", "armor", "accessory", "consumable", "key_item", "material"]
    },
    "rarity": {
      "type": "string",
      "enum": ["common", "uncommon", "rare", "epic", "legendary"],
      "default": "common"
    },
    "value": {
      "type": "integer",
      "minimum": 0,
      "default": 0,
      "description": "Gold value"
    },
    "stackable": {
      "type": "boolean",
      "default": true
    },
    "max_stack": {
      "type": "integer",
      "minimum": 1,
      "default": 99
    },
    "icon": {
      "type": "string",
      "description": "Sprite path"
    },
    "stats": {
      "$ref": "#/definitions/ItemStats"
    },
    "effects": {
      "type": "array",
      "items": { "$ref": "#/definitions/ItemEffect" }
    },
    "equip_slot": {
      "type": "string",
      "enum": ["weapon", "head", "body", "hands", "feet", "accessory_1", "accessory_2"]
    },
    "requirements": {
      "$ref": "#/definitions/Requirements"
    }
  },
  "definitions": {
    "ItemStats": {
      "type": "object",
      "properties": {
        "attack": { "type": "integer", "default": 0 },
        "defense": { "type": "integer", "default": 0 },
        "magic_attack": { "type": "integer", "default": 0 },
        "magic_defense": { "type": "integer", "default": 0 },
        "speed": { "type": "integer", "default": 0 },
        "hp_bonus": { "type": "integer", "default": 0 },
        "mp_bonus": { "type": "integer", "default": 0 }
      }
    },
    "ItemEffect": {
      "type": "object",
      "required": ["type", "value"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["heal_hp", "heal_mp", "cure_status", "buff", "damage"]
        },
        "value": { "type": "integer" },
        "duration": { "type": "number", "description": "Seconds, for buffs" }
      }
    },
    "Requirements": {
      "type": "object",
      "properties": {
        "level": { "type": "integer", "minimum": 1 },
        "class": { "type": "string" },
        "strength": { "type": "integer" }
      }
    }
  }
}
```

### 2. Enemy Schema (`schemas/enemy.schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Enemy",
  "type": "object",
  "required": ["id", "name", "stats"],
  "properties": {
    "id": { "type": "string", "pattern": "^[a-z][a-z0-9_]*$" },
    "name": { "type": "string" },
    "description": { "type": "string" },
    "sprite": { "type": "string" },
    "category": {
      "type": "string",
      "enum": ["slime", "undead", "beast", "demon", "dragon", "humanoid", "elemental", "boss"]
    },
    "stats": {
      "type": "object",
      "required": ["hp", "attack", "defense"],
      "properties": {
        "hp": { "type": "integer", "minimum": 1 },
        "mp": { "type": "integer", "default": 0 },
        "attack": { "type": "integer", "minimum": 0 },
        "defense": { "type": "integer", "minimum": 0 },
        "magic_attack": { "type": "integer", "default": 0 },
        "magic_defense": { "type": "integer", "default": 0 },
        "speed": { "type": "integer", "default": 10 },
        "evasion": { "type": "number", "minimum": 0, "maximum": 1, "default": 0 },
        "critical_rate": { "type": "number", "minimum": 0, "maximum": 1, "default": 0.05 }
      }
    },
    "rewards": {
      "type": "object",
      "properties": {
        "exp": { "type": "integer", "minimum": 0 },
        "gold": { "type": "integer", "minimum": 0 },
        "drops": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["item_id", "chance"],
            "properties": {
              "item_id": { "type": "string" },
              "chance": { "type": "number", "minimum": 0, "maximum": 1 },
              "quantity": { "type": "integer", "default": 1 }
            }
          }
        }
      }
    },
    "skills": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Skill IDs this enemy can use"
    },
    "ai_behavior": {
      "type": "string",
      "enum": ["aggressive", "defensive", "support", "random", "scripted"],
      "default": "aggressive"
    },
    "weaknesses": {
      "type": "array",
      "items": { "type": "string", "enum": ["fire", "ice", "lightning", "holy", "dark", "physical"] }
    },
    "resistances": {
      "type": "array",
      "items": { "type": "string" }
    },
    "is_boss": { "type": "boolean", "default": false }
  }
}
```

### 3. Skill Schema (`schemas/skill.schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Skill",
  "type": "object",
  "required": ["id", "name", "type"],
  "properties": {
    "id": { "type": "string" },
    "name": { "type": "string" },
    "description": { "type": "string" },
    "type": {
      "type": "string",
      "enum": ["attack", "magic", "heal", "buff", "debuff", "utility"]
    },
    "element": {
      "type": "string",
      "enum": ["none", "fire", "ice", "lightning", "holy", "dark"],
      "default": "none"
    },
    "mp_cost": { "type": "integer", "minimum": 0, "default": 0 },
    "cooldown": { "type": "number", "minimum": 0, "default": 0 },
    "target": {
      "type": "string",
      "enum": ["self", "single_ally", "all_allies", "single_enemy", "all_enemies", "random_enemy"],
      "default": "single_enemy"
    },
    "power": { "type": "integer", "description": "Base damage/heal amount" },
    "accuracy": { "type": "number", "minimum": 0, "maximum": 1, "default": 1 },
    "effects": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "status": { "type": "string" },
          "chance": { "type": "number" },
          "duration": { "type": "number" }
        }
      }
    },
    "animation": { "type": "string" },
    "sound": { "type": "string" },
    "learn_level": { "type": "integer", "description": "Level when learned" },
    "class_restriction": {
      "type": "array",
      "items": { "type": "string" }
    }
  }
}
```

### 4. Quest Schema (`schemas/quest.schema.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Quest",
  "type": "object",
  "required": ["id", "name", "objectives"],
  "properties": {
    "id": { "type": "string" },
    "name": { "type": "string" },
    "description": { "type": "string" },
    "type": {
      "type": "string",
      "enum": ["main", "side", "repeatable", "hidden"],
      "default": "side"
    },
    "giver_npc": { "type": "string", "description": "NPC ID who gives the quest" },
    "prerequisites": {
      "type": "object",
      "properties": {
        "quests": { "type": "array", "items": { "type": "string" } },
        "level": { "type": "integer" },
        "flags": { "type": "array", "items": { "type": "string" } }
      }
    },
    "objectives": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type", "target"],
        "properties": {
          "type": {
            "type": "string",
            "enum": ["kill", "collect", "talk", "reach", "escort", "interact"]
          },
          "target": { "type": "string" },
          "count": { "type": "integer", "default": 1 },
          "description": { "type": "string" }
        }
      }
    },
    "rewards": {
      "type": "object",
      "properties": {
        "exp": { "type": "integer" },
        "gold": { "type": "integer" },
        "items": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "item_id": { "type": "string" },
              "quantity": { "type": "integer", "default": 1 }
            }
          }
        },
        "unlock_quests": { "type": "array", "items": { "type": "string" } },
        "set_flags": { "type": "array", "items": { "type": "string" } }
      }
    },
    "dialog": {
      "type": "object",
      "properties": {
        "accept": { "type": "string" },
        "in_progress": { "type": "string" },
        "complete": { "type": "string" }
      }
    }
  }
}
```

## Sample Data Files

### `database/items/weapons.json`

```json
{
  "items": [
    {
      "id": "rusty_sword",
      "name": "Rusty Sword",
      "description": "A worn blade, but still sharp enough.",
      "type": "weapon",
      "rarity": "common",
      "value": 50,
      "icon": "items/weapons/rusty_sword.png",
      "equip_slot": "weapon",
      "stats": { "attack": 5 }
    },
    {
      "id": "iron_sword",
      "name": "Iron Sword",
      "description": "A reliable sword forged from iron.",
      "type": "weapon",
      "rarity": "common",
      "value": 200,
      "icon": "items/weapons/iron_sword.png",
      "equip_slot": "weapon",
      "stats": { "attack": 12 }
    },
    {
      "id": "flame_blade",
      "name": "Flame Blade",
      "description": "A magical sword wreathed in eternal fire.",
      "type": "weapon",
      "rarity": "rare",
      "value": 1500,
      "icon": "items/weapons/flame_blade.png",
      "equip_slot": "weapon",
      "stats": { "attack": 25, "magic_attack": 10 },
      "effects": [{ "type": "damage", "value": 5 }]
    }
    // ... Generate 20-30 weapons total
  ]
}
```

### `database/enemies/slimes.json`

```json
{
  "enemies": [
    {
      "id": "green_slime",
      "name": "Green Slime",
      "description": "A common gelatinous creature found in grasslands.",
      "sprite": "enemies/slime_green.png",
      "category": "slime",
      "stats": {
        "hp": 20,
        "attack": 5,
        "defense": 2,
        "speed": 8
      },
      "rewards": {
        "exp": 5,
        "gold": 3,
        "drops": [
          { "item_id": "slime_gel", "chance": 0.5 }
        ]
      },
      "ai_behavior": "aggressive"
    },
    {
      "id": "blue_slime",
      "name": "Blue Slime",
      "description": "A slime infused with water magic.",
      "sprite": "enemies/slime_blue.png",
      "category": "slime",
      "stats": {
        "hp": 30,
        "mp": 10,
        "attack": 6,
        "defense": 4,
        "magic_attack": 8,
        "speed": 10
      },
      "rewards": {
        "exp": 10,
        "gold": 8,
        "drops": [
          { "item_id": "slime_gel", "chance": 0.6 },
          { "item_id": "water_crystal", "chance": 0.1 }
        ]
      },
      "skills": ["water_splash"],
      "weaknesses": ["lightning"],
      "resistances": ["fire"],
      "ai_behavior": "aggressive"
    },
    {
      "id": "king_slime",
      "name": "King Slime",
      "description": "The crowned ruler of all slimes. Massive and menacing.",
      "sprite": "enemies/slime_king.png",
      "category": "slime",
      "stats": {
        "hp": 500,
        "mp": 50,
        "attack": 25,
        "defense": 15,
        "magic_attack": 20,
        "speed": 6
      },
      "rewards": {
        "exp": 200,
        "gold": 150,
        "drops": [
          { "item_id": "slime_crown", "chance": 0.1 },
          { "item_id": "royal_jelly", "chance": 0.3 }
        ]
      },
      "skills": ["slime_rain", "royal_bounce", "summon_slimes"],
      "is_boss": true,
      "ai_behavior": "scripted"
    }
    // ... Generate 10-15 slime variants
  ]
}
```

## Deliverables

1. **6 JSON Schema files** in `game/data/schemas/`
2. **12+ data files** in `game/data/database/`
3. **3 template files** in `game/data/templates/`
4. **Data loader utility** in `engine/resources/database.py` (update existing)

## Verification

```python
import json
import jsonschema

# Load schema
with open("game/data/schemas/item.schema.json") as f:
    schema = json.load(f)

# Load data
with open("game/data/database/items/weapons.json") as f:
    data = json.load(f)

# Validate each item
for item in data["items"]:
    jsonschema.validate(item, schema)
    print(f"✓ {item['id']} is valid")
```

---

# Task 3: Shader Extraction & Documentation

## Priority: MEDIUM

## Overview

Currently, all 13 GLSL shaders are embedded as Python strings. Extract them to separate `.glsl` files and add documentation.

## Current State

Shaders are embedded in:
- `engine/graphics/batch.py` (2 shaders)
- `engine/graphics/postfx.py` (7 shaders)
- `engine/graphics/particles.py` (2 shaders)
- `engine/graphics/lighting.py` (2 shaders, if separate)

## Target Structure

```
engine/graphics/shaders/
├── README.md                    # Shader documentation
├── common/
│   └── constants.glsl          # Shared constants (#define)
├── sprite/
│   ├── batch.vert              # Sprite batch vertex shader
│   └── batch.frag              # Sprite batch fragment (with lighting)
├── particles/
│   ├── particle.vert           # Instanced particle vertex
│   └── particle.frag           # Particle fragment
├── postfx/
│   ├── fullscreen.vert         # Shared fullscreen quad vertex
│   ├── bloom_bright.frag       # Bloom threshold extraction
│   ├── bloom_blur.frag         # Gaussian blur
│   ├── bloom_combine.frag      # Bloom compositing
│   ├── vignette.frag           # Vignette effect
│   ├── color_grade.frag        # Color grading
│   └── fade.frag               # Screen fade transitions
└── lighting/
    └── point_light.glsl        # Point light calculation (include)
```

## Shader Loader Update

Update `engine/graphics/context.py` to load shaders from files:

```python
class GraphicsContext:
    def load_shader(self, name: str) -> moderngl.Program:
        """Load shader from files.

        Args:
            name: Shader name like "sprite/batch" or "postfx/bloom_blur"

        Returns:
            Compiled ModernGL program
        """
        shader_dir = Path(__file__).parent / "shaders"

        vert_path = shader_dir / f"{name}.vert"
        frag_path = shader_dir / f"{name}.frag"

        # Fall back to shared vertex shader for post-fx
        if not vert_path.exists():
            vert_path = shader_dir / "postfx/fullscreen.vert"

        vert_src = vert_path.read_text()
        frag_src = frag_path.read_text()

        # Handle #include directives
        frag_src = self._process_includes(frag_src, shader_dir)

        return self.ctx.program(
            vertex_shader=vert_src,
            fragment_shader=frag_src
        )

    def _process_includes(self, source: str, base_dir: Path) -> str:
        """Process #include "path" directives."""
        import re
        pattern = r'#include\s+"([^"]+)"'

        def replace(match):
            include_path = base_dir / match.group(1)
            return include_path.read_text()

        return re.sub(pattern, replace, source)
```

## Shader Documentation (`shaders/README.md`)

```markdown
# JRPG Engine Shaders

## Overview

All shaders use GLSL 3.30 core profile (ModernGL requirement).

## Sprite Rendering

### batch.vert / batch.frag

Renders sprites with:
- Camera offset (uniform vec2 u_camera)
- Texture atlas UV mapping
- Per-sprite color tinting
- Dynamic lighting (up to 16 point lights)

**Uniforms:**
| Name | Type | Description |
|------|------|-------------|
| u_texture | sampler2D | Sprite atlas |
| u_camera | vec2 | Camera world offset |
| u_ambient | vec3 | Ambient light color |
| u_light_count | int | Active point lights (0-16) |
| u_light_positions[16] | vec2 | Light world positions |
| u_light_colors[16] | vec3 | Light RGB colors |
| u_light_radii[16] | float | Light falloff radius |

**Lighting Model:**
- Linear falloff: `intensity = 1.0 - (distance / radius)`
- Additive blending for multiple lights
- Clamped to [0, 1] range

## Post-Processing

### Bloom Pipeline

1. **bloom_bright.frag** - Extract bright pixels (threshold 0.7)
2. **bloom_blur.frag** - Two-pass Gaussian blur (horizontal + vertical)
3. **bloom_combine.frag** - Add bloom to original scene

### Color Grading

**Uniforms:**
| Name | Type | Range | Description |
|------|------|-------|-------------|
| u_brightness | float | -1 to 1 | Additive brightness |
| u_contrast | float | 0 to 2 | Multiplicative contrast |
| u_saturation | float | 0 to 2 | Color saturation |
| u_tint | vec3 | 0 to 1 | Color multiply |

## Particles

Instanced rendering with per-particle:
- Position (vec2)
- Size (float)
- Rotation (float)
- Color (vec4)
- Age/lifetime for interpolation
```

## Deliverables

1. **15 shader files** in `engine/graphics/shaders/`
2. **Updated loader** in `engine/graphics/context.py`
3. **Documentation** in `engine/graphics/shaders/README.md`
4. **Update existing files** to use `load_shader()` instead of embedded strings

## Verification

```python
from engine.graphics.context import GraphicsContext

# Create context
ctx = GraphicsContext()

# Load all shaders
shaders = [
    "sprite/batch",
    "particles/particle",
    "postfx/bloom_bright",
    "postfx/bloom_blur",
    "postfx/bloom_combine",
    "postfx/vignette",
    "postfx/color_grade",
    "postfx/fade"
]

for name in shaders:
    program = ctx.load_shader(name)
    print(f"✓ {name} compiled successfully")
```

---

# Task 4: Sample Game Content

## Priority: MEDIUM

## Overview

Generate comprehensive sample game content to demonstrate engine capabilities and enable testing.

## Content Scope

| Category | Count | Description |
|----------|-------|-------------|
| Items | 100+ | Weapons, armor, consumables, materials |
| Enemies | 50+ | Various categories, 5+ bosses |
| Skills | 60+ | Attack, magic, buffs, heals |
| Quests | 20+ | Main story, side quests |
| NPCs | 30+ | Shopkeepers, quest givers, townsfolk |
| Dialog | 50+ | Conversations, tutorials |

## Guidelines

### Items
- Balanced progression (weak → strong)
- Meaningful stat differences
- Interesting effects (not just +ATK)
- Lore-friendly descriptions

### Enemies
- Scaling difficulty curves
- Themed enemy groups (forest, dungeon, castle)
- Interesting AI behaviors
- Boss mechanics (phases, special attacks)

### Skills
- Class identity (warrior = physical, mage = magic)
- MP cost balance
- Interesting tactical choices
- Cool names and descriptions

### Quests
- Clear objectives
- Narrative hooks
- Meaningful rewards
- Branching where appropriate

## Files to Create

```
game/data/database/
├── items/
│   ├── weapons.json          # 25 weapons
│   ├── armor.json            # 25 armor pieces
│   ├── accessories.json      # 15 accessories
│   ├── consumables.json      # 20 consumables
│   ├── materials.json        # 15 crafting materials
│   └── key_items.json        # 10 story items
├── enemies/
│   ├── forest.json           # 10 forest enemies
│   ├── dungeon.json          # 10 dungeon enemies
│   ├── castle.json           # 10 castle enemies
│   ├── elemental.json        # 10 elemental enemies
│   └── bosses.json           # 8 boss enemies
├── skills/
│   ├── warrior.json          # 15 warrior skills
│   ├── mage.json             # 15 mage skills
│   ├── healer.json           # 15 healer skills
│   └── common.json           # 15 universal skills
├── quests/
│   ├── main_story.json       # 10 main quests
│   └── side_quests.json      # 15 side quests
├── npcs/
│   ├── merchants.json        # 8 shopkeepers
│   ├── quest_givers.json     # 12 quest NPCs
│   └── townsfolk.json        # 15 ambient NPCs
└── dialog/
    ├── tutorial.json         # 10 tutorial dialogs
    └── ambient.json          # 40 ambient dialogs
```

## Verification

```python
import json
from pathlib import Path

data_dir = Path("game/data/database")

# Count all entries
total = 0
for json_file in data_dir.rglob("*.json"):
    with open(json_file) as f:
        data = json.load(f)
        # Count items in first array found
        for key, value in data.items():
            if isinstance(value, list):
                count = len(value)
                total += count
                print(f"{json_file.name}: {count} entries")
                break

print(f"\nTotal game content entries: {total}")
# Expected: 300+
```

---

# Task 5: Documentation

## Priority: LOW (Can Run Parallel)

## Overview

Generate comprehensive documentation for areas currently lacking coverage.

## Files to Create

```
docs/
├── architecture/
│   ├── ecs.md                 # Entity-Component-System explanation
│   ├── rendering.md           # GPU pipeline documentation
│   ├── events.md              # Event system guide
│   └── scenes.md              # Scene management
├── guides/
│   ├── quickstart.md          # Getting started tutorial
│   ├── first_game.md          # Build your first game
│   ├── custom_component.md    # Creating new components
│   ├── custom_system.md       # Creating new systems
│   └── modding.md             # Extending the engine
├── reference/
│   ├── components.md          # All component fields
│   ├── systems.md             # All system behaviors
│   ├── events.md              # All event types
│   └── shaders.md             # Shader uniforms/inputs
└── formats/
    ├── item_format.md         # Item JSON specification
    ├── enemy_format.md        # Enemy JSON specification
    ├── dialog_format.md       # Dialog script format
    └── map_format.md          # Tiled map requirements
```

## Documentation Style

- Clear, concise explanations
- Code examples for every concept
- Cross-references between related docs
- Avoid redundancy with docstrings

---

# Execution Order

```
┌─────────────────────────────────────────────────────────┐
│  Priority 1: Test Suite (blocks quality assurance)      │
│  ↓                                                      │
│  Priority 2: JSON Schemas (enables data-driven dev)     │
│  ↓                                                      │
│  Priority 3: Sample Game Data (enables testing)         │
│  ↓                                                      │
│  Priority 4: Shader Extraction (cleanup/maintenance)    │
│  ↓                                                      │
│  Priority 5: Documentation (can run in parallel)        │
└─────────────────────────────────────────────────────────┘
```

---

# Reference Files

Before starting any task, read these files to understand patterns:

```
# Architecture
engine/core/component.py      # Component base (Pydantic)
engine/core/system.py         # System base
engine/core/events.py         # Event bus + Enums
engine/core/world.py          # Entity container

# Examples
framework/components/transform.py    # Example component
framework/components/combat.py       # Complex component
framework/systems/movement.py        # Example system
framework/battle/actions.py          # Complex logic

# Existing verification
verify_codebase.py            # Current test patterns

# Previous handoff
GEMINI_AUDIO_PROMPT.md        # Audio task spec (completed)
```

---

*Generated by Claude Code - 2025-12-25*
