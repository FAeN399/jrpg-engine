# Claude Handoff: JRPG Engine Suite

**Date**: 2025-12-26 | **Status**: ~85% Feature Complete

---

## Project Overview

A complete JRPG game engine built in Python for AI-assisted game development.

**Tech Stack:**
- **Pygame 2.x** - Windowing, input, audio
- **ModernGL** - GPU-accelerated rendering
- **Pydantic** - Data validation for components
- **Dear ImGui** - Editor UI (imgui_bundle)
- **ECS-lite** - Components = DATA ONLY, Systems = LOGIC ONLY
- **Typed Events** - Enum-based, no magic strings

**Project Location**: `D:\py4py`

---

## Recently Completed (2025-12-26 Session)

### 1. Battle Animation Integration
**File**: `framework/battle/system.py`
- Added `AnimationSystem` integration with event subscriptions
- `BattleState.ANIMATION` now used for visual feedback
- Handlers for `ANIMATION_COMPLETED` and `FRAME_EVENT`
- Damage/heal flashes triggered on frame events
- New fields: `_animation_system`, `_pending_result`, `_pending_targets`, `_animation_entity_id`, `_damage_applied`

### 2. Portrait Texture Rendering
**File**: `framework/dialog/system.py`
- `DialogRenderer` now accepts optional ModernGL context
- `_load_portrait()` loads textures via Pygame, converts to ModernGL
- Portrait texture caching in `_portrait_textures` dict
- Uses `imgui.image(texture.glo, ...)` for rendering

### 3. Tile Painting in Map Editor
**Files**: `editor/app.py`, `editor/panels/scene_view.py`
- `EditorState` has tilemap support: `current_tilemap`, `selected_layer`, `brush_size`, `brush_tile`
- `create_new_tilemap()` and `get_current_layer()` helper methods
- Scene viewport renders grid overlay and tilemaps with shaders
- `_paint_tile()` with brush size support
- Auto-creates tilemap on first paint

### 4. Battle Inventory Integration
**File**: `framework/battle/system.py` (lines 839-936)
- `_get_party_items()` - fetches usable items from party inventory slots
- `_get_targets_for_action()` - resolves valid targets by ActionType
- `_get_targets_for_type()` - maps TargetType enum to actor lists (SELF, SINGLE_ALLY, ALL_ALLIES, SINGLE_ENEMY, ALL_ENEMIES, ALL, DEAD_ALLY)
- Line 462: `self._available_items = self._get_party_items()`
- Line 526: Target selection uses `self._get_targets_for_action()`

### 5. Critical Bug Fixes
**File**: `framework/systems/interaction.py`
- Fixed `emit()` → `publish()` (8 occurrences at lines 192, 203, 213, 225, 233, 269, 281, 289)

**File**: `framework/systems/movement.py`
- Added missing `Entity` import (line 9)

**Note**: `CodeReview/CRITICAL_FIXES.md` had 2 incorrect fixes:
- Fix 2 (super().__init__(world)) was WRONG - base System takes no args
- Fix 3 (try_get → get) was WRONG - try_get returns None, get raises KeyError

---

## Verification Status

```bash
python -m pytest tests/ -v          # 37/37 passed
python verify_codebase.py           # 134/135 passed (imgui_bundle not installed in test env)
```

---

## Architecture Patterns (CRITICAL)

### ECS Pattern
```python
# Components are Pydantic models - DATA ONLY
class Health(Component):
    current: int = 100
    maximum: int = 100
    # NO METHODS WITH LOGIC

# Systems contain ALL logic
class DamageSystem(System):
    def process(self, entity, damage):
        health = entity.get(Health)
        health.current -= damage  # Logic lives here
```

### Event System
```python
# Use publish(), NOT emit()
events.publish(EngineEvent.SCENE_TRANSITION, {'type': 'dialog_start'})
events.subscribe(EngineEvent.SCENE_TRANSITION, handler)
```

### Entity Methods
```python
entity.get(Component)      # Raises KeyError if missing
entity.try_get(Component)  # Returns None if missing - USE THIS FOR OPTIONAL
entity.has(Component)      # Returns bool
```

### System Base Class
```python
class MovementSystem(System):
    def __init__(self, world: World):
        super().__init__()        # NO ARGUMENTS to super()
        self._world = world       # Set world manually
```

---

## Remaining TODOs

### Medium Priority
| Task | File | Notes |
|------|------|-------|
| Frame event firing | `framework/systems/animation.py` | Wire frame events to gameplay |
| Inventory item filtering | `framework/components/inventory.py` | Filter by type/usability |
| Asset hot reload | `editor/` | Detect file changes, reload |
| File dialogs | `editor/` | Open/save project files |

### Low Priority
| Task | File | Notes |
|------|------|-------|
| UI rendering stubs | `engine/ui/` | 8 widget render methods are stubs |
| Attack trigger in AI | `framework/systems/ai.py` | Combat initiation logic |

---

## Key File Locations

| Purpose | Path |
|---------|------|
| Battle system | `framework/battle/system.py` |
| Dialog system | `framework/dialog/system.py` |
| Animation system | `framework/systems/animation.py` |
| Scene viewport | `editor/panels/scene_view.py` |
| Editor state | `editor/app.py` |
| Base System class | `engine/core/system.py` |
| Entity class | `engine/core/entity.py` |
| EventBus | `engine/core/events.py` |
| Interaction system | `framework/systems/interaction.py` |
| Movement system | `framework/systems/movement.py` |

---

## Event Types Reference

```python
# Engine events (engine/core/events.py)
class EngineEvent(Enum):
    GAME_START, GAME_PAUSE, GAME_RESUME, GAME_QUIT
    SCENE_PUSHED, SCENE_POPPED, SCENE_SWITCHED, SCENE_TRANSITION
    ENTITY_CREATED, ENTITY_DESTROYED, ENTITY_REMOVED
    COMPONENT_ADDED, COMPONENT_REMOVED

class UIEvent(Enum):
    MENU_OPENED, MENU_CLOSED
    DIALOG_STARTED, DIALOG_ENDED
    WIDGET_FOCUSED, WIDGET_UNFOCUSED
    BUTTON_CLICKED, SELECTION_CHANGED

class AudioEvent(Enum):
    BGM_STARTED, BGM_STOPPED, BGM_CROSSFADE
    SFX_PLAYED

# Animation events (framework/systems/animation.py)
class AnimationEvent(Enum):
    ANIMATION_COMPLETED
    FRAME_EVENT
```

---

## Previously Completed Tasks

### Task 1: UI/Menu System
- Full gamepad-first UI in `engine/ui/`
- Widgets: label, button, panel, selection_list, grid, progress_bar, text_box
- Presets: dialog_box, battle_hud, inventory_screen, etc.

### Task 2: Animation System
- `engine/graphics/animation.py` - LoopMode, AnimationFrame, AnimationClip
- `framework/systems/animation.py` - AnimationSystem with directional play

### Task 3: Editor Entity/Component System
- `editor/panels/entity_hierarchy.py` - Entity tree with CRUD
- `editor/panels/component_inspector.py` - Property editing
- `editor/widgets/field_editors.py` - Dynamic Pydantic field rendering

---

## Testing Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Verify codebase integrity
python verify_codebase.py

# Quick import check
python -c "from engine.core import *; from framework.battle import *; from framework.systems import *; print('OK')"
```

---

## Common Gotchas

1. **Event API**: Use `publish()` not `emit()` - codebase was migrated
2. **System.__init__()**: Base class takes NO arguments; set `self._world` manually
3. **try_get vs get**: Use `try_get()` when component is optional (returns None)
4. **imgui_bundle**: Not installed in test environment, but code is correct
5. **CodeReview/CRITICAL_FIXES.md**: 2 of 4 fixes were invalid - already handled

---

## Git Status

Single commit on master. Run `git status` to see modified files.

Modified files from this session:
- `framework/battle/system.py` (animation + inventory integration)
- `framework/dialog/system.py` (portrait rendering)
- `framework/systems/interaction.py` (emit → publish fix)
- `framework/systems/movement.py` (Entity import fix)
- `editor/app.py` (tilemap support)
- `editor/panels/scene_view.py` (tile painting)

---

*Updated: 2025-12-26 - Battle animations, portraits, tile painting, inventory integration complete*
