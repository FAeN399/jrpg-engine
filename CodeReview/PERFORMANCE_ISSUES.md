# Performance Issues - Hot Path Optimization

These issues don't crash but will hurt FPS in production.

---

## 1. SpriteBatch Vertex Buffer (batch.py)

**Current** (Slow):
```python
self._vertices: list[float] = []
# ...
self._vertices.extend([x0, y0, u0, v0, r, g, b, a, ...])
# ...
data = struct.pack(f'{len(self._vertices)}f', *self._vertices)
```

**Problem**:
- Python list has poor cache locality
- `extend()` may trigger resize/copy
- `struct.pack(*list)` unpacks entire list as function arguments

**Recommended**:
```python
import array

class SpriteBatch:
    def __init__(self, ...):
        # Pre-allocate with capacity
        self._vertices = array.array('f', [0.0] * (max_sprites * self.FLOATS_PER_SPRITE))
        self._vertex_count = 0

    def _add_sprite_vertices(self, sprite):
        i = self._vertex_count
        v = self._vertices
        # Direct index assignment (no allocation)
        v[i] = x0; v[i+1] = y0; v[i+2] = u0; ...
        self._vertex_count += 48  # 6 vertices * 8 floats

    def _flush(self):
        # Zero-copy bytes view
        data = memoryview(self._vertices)[:self._vertex_count * 4].tobytes()
        self.vbo.write(data)
```

**Expected Improvement**: 5-10x faster vertex submission

---

## 2. Event Queue (events.py:275)

**Current** (O(n)):
```python
while self._event_queue:
    queued = self._event_queue.pop(0)  # Shifts entire list!
```

**Recommended** (O(1)):
```python
from collections import deque

self._event_queue: deque[Event] = deque()
# ...
queued = self._event_queue.popleft()
```

---

## 3. Import Inside Method (batch.py:272)

**Current**:
```python
def _add_sprite_vertices(self, sprite):
    import math  # Module lookup every sprite!
```

**Recommended**:
```python
import math  # At module level

class SpriteBatch:
    def _add_sprite_vertices(self, sprite):
        # math already imported
```

---

## 4. Function Creation in Loop (batch.py:289)

**Current**:
```python
def _add_sprite_vertices(self, sprite):
    if sprite.rotation != 0.0:
        cos_r = math.cos(sprite.rotation)
        sin_r = math.sin(sprite.rotation)

        def rotate(x, y):  # New function object every sprite!
            return x * cos_r - y * sin_r, x * sin_r + y * cos_r

        x0, y0 = rotate(x0, y0)
        x1, y1 = rotate(x1, y1)
        ...
```

**Recommended** (inline):
```python
if sprite.rotation != 0.0:
    cos_r = math.cos(sprite.rotation)
    sin_r = math.sin(sprite.rotation)

    # Inline rotation - no function allocation
    x0, y0 = x0 * cos_r - y0 * sin_r, x0 * sin_r + y0 * cos_r
    x1, y1 = x1 * cos_r - y1 * sin_r, x1 * sin_r + y1 * cos_r
    x2, y2 = x2 * cos_r - y2 * sin_r, x2 * sin_r + y2 * cos_r
    x3, y3 = x3 * cos_r - y3 * sin_r, x3 * sin_r + y3 * cos_r
```

---

## 5. Duplicate Quad VBOs (postfx.py)

**Current**: Each PostEffect creates identical fullscreen quad:
- `BloomEffect._create_quad()`
- `VignetteEffect._create_quad()`
- `ColorGradeEffect._create_quad()`
- `FadeEffect._create_quad()`

**Recommended**: Share single quad buffer:
```python
class PostProcessingChain:
    def __init__(self, ctx, width, height):
        self._shared_quad_vbo = self._create_quad_vbo()

    def enable_vignette(self, ...):
        self.vignette = VignetteEffect(self.ctx, self._shared_quad_vbo, ...)
```

---

## 6. Shader Path Loading (batch.py:97-99)

**Current**:
```python
vertex_src = Path("engine/graphics/shaders/sprite/batch.vert").read_text()
```

**Problem**: Relative path fails if CWD != project root

**Recommended**:
```python
from pathlib import Path

_SHADER_DIR = Path(__file__).parent / "shaders"

class SpriteBatch:
    def __init__(self, ctx, ...):
        vertex_src = (_SHADER_DIR / "sprite/batch.vert").read_text()
```

---

## Profiling Commands

```python
# Add to game loop for basic timing
import time

class Game:
    def update(self, dt):
        t0 = time.perf_counter()
        self.sprite_batch.end()
        render_time = time.perf_counter() - t0
        if render_time > 0.016:  # > 16ms = < 60fps
            print(f"Slow render: {render_time*1000:.1f}ms")
```

For detailed profiling:
```bash
python -m cProfile -s cumtime your_game.py
```
