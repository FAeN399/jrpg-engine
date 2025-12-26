# Directory Log: framework/
**Date:** 2025-12-25
**Logger:** AI Log Man Robot

---

## Overview

The `framework/` directory contains **JRPG-specific game systems** built on top of the core engine. This is reusable code for creating JRPGs, not game-specific content.

**Total Files:** 32 Python files
**Architecture:** Data-only components (Pydantic), logic-only systems

---

## File Structure

```
framework/
  __init__.py               # Module docstring

  components/               # Data-only components (Pydantic)
    __init__.py             # Re-exports all components
    transform.py            # Position, velocity, direction (158 lines)
    physics.py              # Collision shapes
    character.py            # Stats, health, mana, experience
    combat.py               # Combat stats, status effects
    inventory.py            # Items, slots, equipment
    dialog.py               # Dialog state, nodes, choices
    ai.py                   # AI behaviors, patrol paths
    interaction.py          # Interaction triggers

  systems/                  # Logic processors (System subclasses)
    __init__.py
    movement.py             # Applies velocity to transform
    collision.py            # Collision detection/response
    ai.py                   # AI behavior execution
    interaction.py          # Trigger handling

  world/                    # World management
    __init__.py
    map.py                  # Map loading, tile data
    player.py               # Player entity factory
    npc.py                  # NPC entity factory

  dialog/                   # Conversation system
    __init__.py
    system.py               # DialogManager, DialogRenderer (482 lines)
    parser.py               # Script parser (custom format)

  battle/                   # Turn-based combat
    __init__.py
    actor.py                # BattleActor, enemy data
    actions.py              # Action executor (attack, skill, item)
    system.py               # BattleSystem controller (706 lines)

  progression/              # Character progression
    __init__.py
    skills.py               # Skill definitions
    quests.py               # QuestManager (348 lines)

  inventory/                # Item management
    __init__.py
    items.py                # Item definitions

  save/                     # Persistence
    __init__.py
    manager.py              # SaveManager (404 lines)
```

---

## Component Analysis

### components/transform.py
**Classes:**
- `Direction` - 8 cardinal/ordinal directions with vector conversion
- `Transform` - Position (x,y,z), rotation, scale, facing
- `Velocity` - Movement speed, friction, max speed

**Key Features:**
- `tile_position` property for grid-based movement
- `distance_to()` for range calculations
- Velocity clamping and friction

---

### components/character.py
**Classes:**
- `CharacterStats` - STR, DEF, MAG, RES, AGI, LCK
- `Health` - Current/max HP with damage/heal methods
- `Mana` - Current/max MP with consume/restore
- `Experience` - Level, EXP, leveling logic

---

### components/combat.py
**Classes:**
- `CombatStats` - ATK power, critical rate, evasion
- `StatusEffect` - Effect type, duration, stacking
- `ElementalAffinity` - Weakness/resistance system

---

### components/inventory.py
**Classes:**
- `Inventory` - Item slots, max capacity, gold
- `InventorySlot` - Item ID, quantity
- `Equipment` - Equipment slots (weapon, armor, accessory)

---

## System Analysis

### battle/system.py - BattleSystem (706 lines)
**Purpose:** Complete turn-based combat controller.

**State Machine:**
```
NONE -> STARTING -> TURN_START -> PLAYER_INPUT/ENEMY_AI
     -> TARGET_SELECT -> EXECUTING -> TURN_END
     -> VICTORY/DEFEAT/FLED -> ENDING
```

**Features:**
- Speed-based turn order
- Command menu (Attack, Skill, Item, Defend, Flee)
- Target selection
- Status effect processing (poison, burn, regen)
- EXP/reward distribution
- Simple enemy AI (random target selection)

**Note:** Uses `events.emit()` which should be `events.publish()` (API mismatch).

---

### dialog/system.py - DialogManager (482 lines)
**Purpose:** JSON-based dialog script execution.

**Features:**
- Dialog loading from JSON files
- Node-based conversation flow
- Choice filtering by condition
- Variable substitution in text
- Typewriter text reveal
- Script execution (on_enter, on_exit, actions)

**DialogRenderer:**
- ImGui-based dialog box rendering
- Portrait placeholder support
- Choice highlighting

**Security Note:** Uses `eval()` and `exec()` for condition/script evaluation. Safe context provided but could be risky with user-generated content.

---

### progression/quests.py - QuestManager (348 lines)
**Purpose:** Quest tracking and progression.

**Features:**
- Quest templates loaded from JSON
- Objective types: TALK, COLLECT, KILL, DELIVER, REACH, INTERACT, CUSTOM
- Progress tracking with current/target counts
- Prerequisite quest checking
- Reward distribution (EXP, gold, items, quest unlocks)
- Save/load integration

---

### save/manager.py - SaveManager (404 lines)
**Purpose:** Game state persistence.

**Features:**
- 10 save slots
- JSON serialization
- Metadata (timestamp, playtime, location, level)
- Player/party data saving
- Quest state integration
- Game flags for story progression
- Inventory persistence

**TODO noted:** Line 402 - "TODO: Restore player position, stats, inventory"

---

## Design Principles

1. **Data-Only Components**
   - Components inherit from `engine.core.component.Component` (Pydantic BaseModel)
   - No game logic in components
   - Use `Field(default_factory=...)` for mutable defaults

2. **Logic-Only Systems**
   - Systems process entities with matching components
   - `required_components` class attribute
   - `process_entity(entity, dt)` for per-entity logic

3. **Event-Driven Communication**
   - Systems publish events via EventBus
   - Loose coupling between subsystems

---

## Potential Issues

### 1. API Mismatch in battle/system.py
**Lines 266, 544, 649:** Uses `events.emit()` but EventBus API is `events.publish()`

### 2. Security Risk in dialog/system.py
**Lines 210, 226:** Uses `eval()` and `exec()` for dialog scripts. While safe context is provided, malformed scripts could cause issues.

### 3. Missing Type in battle/system.py
**Line 355-362:** References `StatusType.PARALYSIS`, `StatusType.SLEEP`, etc. but `StatusType` is not imported.

### 4. Incomplete Save/Load
**save/manager.py:255:** Uses `get_entities_with_components()` but World API is `get_entities_with()`

### 5. Hardcoded Tile Size
**transform.py:94:** `tile_position` assumes 16x16 tiles. Should be configurable.

---

## Dependencies

```python
from engine.core import World, Entity, System, Component
from engine.core.events import EventBus, EngineEvent
from engine.core.actions import Action
```

All framework code depends on the engine core being present.

---

*End of framework/ log*
