# Critical Fixes - Apply Immediately

These 4 bugs will crash at runtime. Fix before any testing.

---

## Fix 1: interaction.py - emit → publish

**File**: `framework/systems/interaction.py`

Replace all occurrences of `self.events.emit(` with `self.events.publish(`

**Lines to fix**: 192, 203, 213, 225, 233, 269, 281, 289

---

## Fix 2: movement.py - Broken super().__init__

**File**: `framework/systems/movement.py`

**Line 26-30** - Change from:
```python
def __init__(self, world: World, game_map: Optional[GameMap] = None):
    super().__init__()
    self._world = world
    self.game_map = game_map
    self.required_components = {Transform, Velocity}
```

**To**:
```python
def __init__(self, world: World, game_map: Optional[GameMap] = None):
    super().__init__(world)
    self.game_map = game_map
    self.required_components = {Transform, Velocity}
```

---

## Fix 3: movement.py - try_get doesn't exist

**File**: `framework/systems/movement.py`

**Line 59** - Change from:
```python
collider = entity.try_get(Collider)
```

**To**:
```python
collider = entity.get(Collider)
```

---

## Fix 4: movement.py - Missing Entity import

**File**: `framework/systems/movement.py`

**Line 9** - Change from:
```python
from engine.core import System, World
```

**To**:
```python
from engine.core import System, World, Entity
```

---

## Verification

After fixes, run:
```bash
python verify_codebase.py
```

All tests should pass.
