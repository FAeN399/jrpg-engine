# Repair Report: JRPG Engine Verification

## Summary
The codebase verification was failing due to structural issues in component definitions and bugs in the verification script itself. All code logic tests now pass.

## 1. Component Refactoring (Major Fix)
**Issue:** `ValueError: mutable default <class> for field ... is not allowed`
**Cause:** Components were mixing `@dataclass` (stdlib) with `Component` (Pydantic BaseModel). Pydantic prohibits mutable defaults like `list` or `dict` unless using `Field(default_factory=...)`, but the `@dataclass` decorator was obscuring this or conflicting with it.

**Fix Applied:**
- Removed `@dataclass` decorator from all Component subclasses in the `framework/components/` directory.
- Replaced standard type annotations with Pydantic `Field` for mutable defaults.
- Renamed `__post_init__` to `model_post_init` (Pydantic hook).
- Added `PrivateAttr` for internal private fields (e.g. `_direction` in `PatrolPath`).

**Affected Files:**
- `framework/components/ai.py`
- `framework/components/character.py`
- `framework/components/combat.py`
- `framework/components/dialog.py`
- `framework/components/interaction.py`
- `framework/components/inventory.py`
- `framework/components/physics.py`
- `framework/components/transform.py`

## 2. Verification Script Fixes
**Issue:** The verification script (`verify_codebase.py`) contained bugs preventing it from correctly testing the engine.

**Fixes Applied:**
- **SceneManager Init**: Passed explicit `None` to `SceneManager(None)` instead of empty `SceneManager()` to fix `TypeError`.
- **EventBus API**: Changed `bus.emit(...)` to `bus.publish(...)` to match the actual `EventBus` implementation.
- **Weak References**: Updated event subscription test to use `weak=False` for lambda functions to prevent immediate garbage collection failures.
- **Fragile Test**: Updated `test_entity_creation` to check `id > 0` instead of `id == 1` to be robust against global counter state.
- **Windows Compatibility**: Replaced Unicode box-drawing characters and checkmarks with ASCII (`[+]`, `[-]`) to prevent `UnicodeEncodeError` on Windows consoles.

## 3. Remaining Observations
- **Missing Dependency**: `imgui-bundle` is missing in the current environment. This affects `Phase 3: Editor` tools but does not break the core engine logic.
