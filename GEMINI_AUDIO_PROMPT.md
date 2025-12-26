# Gemini Task: Implement Audio System for JRPG Engine

## Context

You are working on a JRPG game engine suite built in Python. The engine uses:
- **Pygame 2.x** for windowing, input, and audio
- **ModernGL** for GPU rendering
- **Pydantic** for data validation (components are BaseModel subclasses)
- **ECS-lite architecture**: Components are DATA ONLY, Systems contain LOGIC ONLY

The project is located at `D:\py4py` and has the following relevant structure:
```
engine/
├── core/
│   ├── component.py      # Component base class (Pydantic BaseModel)
│   ├── system.py         # System base class
│   ├── events.py         # EventBus with typed events (Enums)
│   └── world.py          # World container
├── audio/
│   └── __init__.py       # Currently empty - YOUR TASK
```

## Your Task

Implement a complete audio system for JRPG games. Create the following files:

### 1. `engine/audio/manager.py` - Audio Manager

Core audio management with:

**BGM (Background Music) Features:**
- Play/stop/pause/resume background music
- Volume control (0.0 to 1.0)
- Smooth crossfade transitions between tracks (configurable duration)
- Loop support with optional intro section (play intro once, then loop main)
- Fade in/out effects
- Queue system for sequential tracks

**SFX (Sound Effects) Features:**
- Play one-shot sound effects
- Separate volume control from BGM
- Multiple concurrent SFX playback
- Positional audio (2D panning based on world position relative to camera)
- SFX categories (UI, combat, environment, footsteps) with per-category volume
- Sound pooling to prevent excessive channel usage

**General:**
- Master volume control
- Mute toggle (preserves volume settings)
- Audio settings persistence (dict for save/load)
- Graceful handling of missing audio files

### 2. `engine/audio/music.py` - Music Player

Dedicated music playback with:

**Features:**
- Crossfade implementation using pygame.mixer.music
- Track metadata (title, artist, loop_start, loop_end)
- Playlist support with shuffle/repeat modes
- Battle music transitions (save current position, switch, return)
- Dynamic music layers (e.g., add drums when combat starts)

### 3. `engine/audio/components.py` - Audio Components

Pydantic components for entity audio:

```python
class AudioSource(Component):
    """Attach to entities that emit sounds."""
    sound_id: str = ""
    volume: float = 1.0
    loop: bool = False
    spatial: bool = True  # Use positional audio
    max_distance: float = 300.0  # Falloff distance

class AudioListener(Component):
    """Attach to camera/player for positional audio."""
    # Usually just a marker, position comes from Transform
```

### 4. Update `engine/audio/__init__.py`

Export all public classes:
```python
from engine.audio.manager import AudioManager
from engine.audio.music import MusicPlayer
from engine.audio.components import AudioSource, AudioListener
```

## Technical Requirements

1. **Use Pygame's audio system:**
   - `pygame.mixer` for sound effects (8 channels default, expandable)
   - `pygame.mixer.music` for background music (streaming, single channel)

2. **Follow the engine's architecture:**
   - Components inherit from `engine.core.component.Component` (Pydantic BaseModel)
   - Use `Field(default_factory=...)` for mutable defaults
   - No `@dataclass` decorator on Component subclasses
   - Event integration with `engine.core.events.EventBus`

3. **Audio Events (add to engine/core/events.py if needed):**
   ```python
   class AudioEvent(Enum):
       BGM_STARTED = auto()
       BGM_STOPPED = auto()
       BGM_CROSSFADE = auto()
       SFX_PLAYED = auto()
   ```

4. **File format support:**
   - BGM: OGG Vorbis (recommended), MP3, WAV
   - SFX: WAV (low latency), OGG

5. **Error handling:**
   - Log warnings for missing files, don't crash
   - Graceful degradation if audio system fails to initialize

## Example Usage

```python
from engine.audio import AudioManager

# Initialize
audio = AudioManager()
audio.init()

# BGM
audio.play_bgm("music/town_theme.ogg", fade_in=2.0)
audio.crossfade_bgm("music/battle_theme.ogg", duration=1.0)
audio.set_bgm_volume(0.7)

# SFX
audio.play_sfx("sfx/sword_slash.wav")
audio.play_sfx("sfx/footstep.wav", position=(100, 50), category="footsteps")

# Settings
audio.set_master_volume(0.8)
audio.set_category_volume("footsteps", 0.5)
audio.mute(True)

# Save/Load settings
settings = audio.get_settings()  # dict
audio.apply_settings(settings)
```

## File Locations

Create your files at:
- `D:\py4py\engine\audio\manager.py`
- `D:\py4py\engine\audio\music.py`
- `D:\py4py\engine\audio\components.py`
- Update `D:\py4py\engine\audio\__init__.py`

## Reference Files

Before starting, read these files to understand the architecture:
- `D:\py4py\engine\core\component.py` - Component base class
- `D:\py4py\engine\core\events.py` - Event system
- `D:\py4py\engine\core\system.py` - System base class
- `D:\py4py\framework\components\transform.py` - Example component

## Verification

After implementation, the following should work:
```python
# Test imports
from engine.audio import AudioManager, MusicPlayer, AudioSource, AudioListener

# Test instantiation
manager = AudioManager()
assert hasattr(manager, 'play_bgm')
assert hasattr(manager, 'play_sfx')
assert hasattr(manager, 'crossfade_bgm')

# Test components
source = AudioSource(sound_id="test", volume=0.5)
assert source.sound_id == "test"
```

## Notes

- Keep implementations focused and practical for JRPG use cases
- Prioritize reliability over complexity
- Use type hints throughout
- Include docstrings for all public methods
- Follow the existing code style in the project
