# QA Code Review Report #5

**File**: `framework/battle/system.py`
**Reviewer**: QA Code Reviewer Agent
**Date**: 2025-12-26

---

## VERDICT: **FAIL** - CRITICAL BUGS PRESENT

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 3 |
| HIGH | 1 |
| MEDIUM | 1 |
| LOW | 0 |

---

## Critical Issues

### CRITICAL-001: Wrong Event Method - `emit` vs `publish` (Multiple Lines)

**Locations**: Lines 297, 379, 601, 714, 791

```python
# Line 297:
self.events.emit(EngineEvent.SCENE_TRANSITION, {...})

# Line 379:
self.events.emit(EngineEvent.SCENE_TRANSITION, {...})

# Line 601:
self.events.emit(EngineEvent.ENTITY_MODIFIED, {...})

# Line 714:
self.events.emit(EngineEvent.SCENE_TRANSITION, {...})

# Line 791:
self.events.emit(EngineEvent.ENTITY_MODIFIED, {...})
```

**Impact**: `AttributeError: 'EventBus' object has no attribute 'emit'` - Every event publish will crash.

**Root Cause**: `EventBus` defines `publish()`, not `emit()`. Inconsistency with `interaction.py` which was fixed.

**Recommended Fix**: Replace all `self.events.emit(` with `self.events.publish(`

---

### CRITICAL-002: Undefined Name `StatusType` (Lines 395-403, 662-674)

**Location**: Lines 395, 401, 662, 667, 672

```python
# Line 395:
if self._current_actor.has_status(StatusType.PARALYSIS):

# Line 401:
if self._current_actor.has_status(StatusType.SLEEP):

# Line 662:
if actor.has_status(StatusType.POISON):

# Line 667:
if actor.has_status(StatusType.BURN):

# Line 672:
if actor.has_status(StatusType.REGEN):
```

**Impact**: `NameError: name 'StatusType' is not defined` - Turn processing and status damage will crash.

**Root Cause**: `StatusType` enum is used but never imported at the top of the file.

**Recommended Fix**: Add import:
```python
from framework.components.combat import StatusType
```
(Verify the actual location of StatusType enum in the codebase)

---

### CRITICAL-003: Non-existent Method `try_get` (Line 854)

**Location**: Line 854

```python
inventory = entity.try_get(Inventory)
```

**Impact**: `AttributeError: 'Entity' object has no attribute 'try_get'`

**Root Cause**: Same issue as in `movement.py`. Entity class uses `get()`, not `try_get()`.

**Recommended Fix**:
```python
inventory = entity.get(Inventory)
```

---

## High Priority Issues

### HIGH-001: Event Callback Naming Collision (Lines 725-726, 938-940)

**Location**: Lines 725-726 and 938-940

```python
# Line 725-726:
if self._on_battle_end:
    self._on_battle_end(rewards)

# Line 938-940:
def on_battle_end(self, callback: Callable[[BattleRewards], None]) -> None:
    """Set callback for battle end."""
    self._on_battle_end = callback
```

**Issue**: The method `_on_battle_end()` on line 691 has the same base name as the callback stored in `self._on_battle_end`. This is confusing and could lead to bugs if someone accidentally calls the wrong one.

**Recommended Fix**: Rename the internal method:
```python
def _handle_battle_end(self) -> None:
    ...
```

---

## Medium Priority Issues

### MEDIUM-001: Potential Index Out of Bounds (Lines 487-490, 507-510)

**Location**: Lines 487-490 and 507-510

```python
# Skills:
if self.input.is_action_pressed(Action.MOVE_UP):
    self._skill_selection = (self._skill_selection - 1) % len(skills)

# Items:
if self.input.is_action_pressed(Action.MOVE_UP):
    self._item_selection = (self._item_selection - 1) % len(items)
```

**Impact**: If `skills` or `items` is empty, `% len(...)` causes `ZeroDivisionError`.

**Note**: The code does check for empty lists before opening submenus (lines 457, 464), but if the list becomes empty during selection (e.g., concurrent modification), this could crash.

---

## Line Reference Table

| Line | Issue | Severity |
|------|-------|----------|
| 297 | `emit` instead of `publish` | CRITICAL |
| 379 | `emit` instead of `publish` | CRITICAL |
| 395 | `StatusType` undefined | CRITICAL |
| 401 | `StatusType` undefined | CRITICAL |
| 601 | `emit` instead of `publish` | CRITICAL |
| 662 | `StatusType` undefined | CRITICAL |
| 667 | `StatusType` undefined | CRITICAL |
| 672 | `StatusType` undefined | CRITICAL |
| 714 | `emit` instead of `publish` | CRITICAL |
| 791 | `emit` instead of `publish` | CRITICAL |
| 854 | `try_get` undefined | CRITICAL |

---

## Positive Observations

1. **Comprehensive Battle State Machine**: Well-defined states and transitions
2. **Turn Order Management**: Clean speed-based ordering with re-sorting each round
3. **Animation Integration**: Proper deferred damage application with frame events
4. **Targeting System**: Flexible target type handling for skills/items
5. **Status Effect Processing**: Poison, Burn, Regen logic is correct (once StatusType is imported)

---

## Security Review

- No security vulnerabilities in battle logic
- No external input injection risks
- Random number usage is appropriate for game mechanics

---

**Status**: BLOCKED - DO NOT EXECUTE UNTIL CRITICAL FIXES APPLIED

## Required Fixes Before Approval

1. Replace all `self.events.emit(` with `self.events.publish(`
2. Import `StatusType` from appropriate module
3. Replace `entity.try_get(Inventory)` with `entity.get(Inventory)`

