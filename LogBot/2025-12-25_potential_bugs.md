# Potential Bugs & Issues Log
**Date:** 2025-12-25
**Logger:** AI Log Man Robot

---

## Critical Issues

### 1. AudioSystem accesses protected members of AudioManager
**File:** `engine/audio/system.py:101-114`
**Severity:** Medium
**Description:**
`AudioSystem.process_entity()` directly accesses protected members:
- `audio_manager._calculate_spatial_volume()`
- `audio_manager._master_volume`
- `audio_manager._category_volumes`

**Risk:** Breaking encapsulation; if AudioManager's internals change, AudioSystem will break silently.

**Recommendation:** Expose public API on AudioManager:
- `calculate_spatial_volume()` (public)
- `get_effective_volume(category, base_volume)` helper

---

### 2. AudioSystem has no `super().__init__()` call
**File:** `engine/audio/system.py:24-27`
**Severity:** Low-Medium
**Description:**
The `__init__` method calls `super().__init__()` but `System` base class behavior should be verified. The system relies on `self._world` being set, which happens in `System.on_add()`.

**Risk:** If `System` base adds initialization logic in the future, this could break.

---

### 3. MusicPlayer crossfade doesn't actually crossfade
**File:** `engine/audio/music.py:105-139`
**Severity:** Low (Known limitation)
**Description:**
The `crossfade()` method documents crossfading but actually does a simple fade-to-new-track. True crossfade (overlapping audio) isn't possible with pygame.mixer.music (single channel).

**Impact:** Audio transitions may feel abrupt compared to games with true crossfade.

**Note:** This is a pygame limitation, not a bug. Consider documenting more clearly.

---

### 4. Sound cache never cleared
**File:** `engine/audio/manager.py:43`
**Severity:** Low
**Description:**
`_sound_cache` dictionary grows indefinitely as new sounds are loaded. No mechanism exists to:
- Clear cache on scene change
- Limit cache size
- Unload unused sounds

**Risk:** Memory leak in long sessions with many unique sound files.

**Recommendation:** Add cache management methods:
- `clear_cache()`
- `unload_sound(file_path)`
- Consider LRU cache with size limit

---

### 5. AudioListener: Multiple active listeners undefined behavior
**File:** `engine/audio/components.py:34-41`
**Severity:** Low
**Description:**
The docstring says "Only one active AudioListener should exist" but there's no enforcement. If multiple listeners are active, `AudioSystem.pre_update()` uses the first one found (iteration order).

**Risk:** Unpredictable spatial audio if developer accidentally creates multiple listeners.

**Recommendation:** Add warning log if multiple active listeners detected.

---

## Potential Issues

### 6. World.get_entities_with returns Iterator
**File:** `engine/core/world.py:233`
**Severity:** Info
**Description:**
Returns `Iterator[Entity]` which can only be consumed once. In `AudioSystem.pre_update()`:
```python
listeners = self._world.get_entities_with(AudioListener, Transform)
for entity in listeners:
```
This works, but if the result is used twice, second iteration yields nothing.

---

### 7. AudioSource.active state management complexity
**File:** `engine/audio/system.py:53-84`
**Severity:** Low
**Description:**
The `active` flag controls playback, but state transitions are complex:
- Set `active=True` -> starts playing
- Channel finishes -> sets `active=False` automatically
- User can set `active=False` -> stops sound

This implicit state mutation (system modifying component) may confuse developers expecting components to be data-only.

---

### 8. EventBus weak references with lambdas
**File:** `engine/core/events.py:134-140`
**Severity:** Documented/Fixed
**Description:**
Lambda functions cannot be weak-referenced properly. This was fixed in verify_codebase.py by using `weak=False`. However, other code may still accidentally use lambdas with default `weak=True`.

**Recommendation:** Add runtime warning when attempting to weak-ref a lambda.

---

## Missing Features (Not Bugs)

### 9. No audio asset verification
**Description:** No startup check that audio files exist. Errors only appear at runtime when sound is played.

### 10. No audio fade-out on game quit
**Description:** Abrupt audio stop when game exits. Should fade BGM.

### 11. No audio ducking
**Description:** No mechanism to lower BGM when voice/SFX plays (common in JRPGs for dialog).

---

## Verification Script Notes

The `verify_codebase.py` script has been fixed for:
- Windows Unicode compatibility
- EventBus API alignment (`publish` vs `emit`)
- SceneManager initialization
- Lambda weak references

All 90+ files verify successfully for structure and imports.

---

*End of bugs log*
