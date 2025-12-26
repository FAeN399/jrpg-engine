"""
Animation data structures and playback controller.

Provides frame-based sprite animation with:
- Multiple animation clips per entity
- Loop modes (once, loop, ping-pong)
- Frame events for gameplay triggers
- Speed control and blending
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Callable, Any


class LoopMode(Enum):
    """Animation loop behavior."""
    ONCE = auto()        # Play once and stop on last frame
    LOOP = auto()        # Loop forever
    PING_PONG = auto()   # Forward then backward, repeating


@dataclass
class AnimationFrame:
    """
    Single frame of animation.

    Attributes:
        region_name: Name of TextureRegion in atlas (or frame index)
        duration: Seconds to display this frame
        offset_x: Pixel offset from origin (for attack animations, etc.)
        offset_y: Pixel offset from origin
        event: Event name to fire when this frame is reached
    """
    region_name: str
    duration: float = 0.1
    offset_x: float = 0.0
    offset_y: float = 0.0
    event: Optional[str] = None

    @classmethod
    def from_index(cls, index: int, duration: float = 0.1) -> 'AnimationFrame':
        """Create frame from sprite sheet index."""
        return cls(region_name=str(index), duration=duration)


@dataclass
class AnimationClip:
    """
    A single animation (e.g., 'walk_right', 'attack_down').

    Clips contain a sequence of frames and playback settings.
    """
    name: str
    frames: List[AnimationFrame] = field(default_factory=list)
    loop_mode: LoopMode = LoopMode.LOOP
    speed_multiplier: float = 1.0

    @property
    def total_duration(self) -> float:
        """Get total animation duration in seconds."""
        return sum(f.duration for f in self.frames)

    @property
    def frame_count(self) -> int:
        """Get number of frames."""
        return len(self.frames)

    def get_frame_at_time(self, time: float) -> tuple[AnimationFrame, int]:
        """
        Get frame for given time.

        Args:
            time: Elapsed time in seconds

        Returns:
            (frame, frame_index) tuple
        """
        if not self.frames:
            raise ValueError(f"Animation '{self.name}' has no frames")

        duration = self.total_duration
        if duration <= 0:
            return self.frames[0], 0

        # Handle looping
        if self.loop_mode == LoopMode.LOOP:
            time = time % duration
        elif self.loop_mode == LoopMode.PING_PONG:
            cycle = duration * 2
            time = time % cycle
            if time > duration:
                time = cycle - time  # Reverse direction
        else:  # ONCE
            time = min(time, duration - 0.0001)

        # Find frame at time
        elapsed = 0.0
        for i, frame in enumerate(self.frames):
            elapsed += frame.duration
            if time < elapsed:
                return frame, i

        # Fallback to last frame
        return self.frames[-1], len(self.frames) - 1

    def add_frame(
        self,
        region_name: str,
        duration: float = 0.1,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        event: Optional[str] = None,
    ) -> 'AnimationClip':
        """Add a frame to the animation (fluent)."""
        self.frames.append(AnimationFrame(
            region_name=region_name,
            duration=duration,
            offset_x=offset_x,
            offset_y=offset_y,
            event=event,
        ))
        return self

    def add_frames(
        self,
        region_names: List[str],
        duration: float = 0.1,
    ) -> 'AnimationClip':
        """Add multiple frames with same duration (fluent)."""
        for name in region_names:
            self.add_frame(name, duration)
        return self

    def add_frames_from_indices(
        self,
        indices: List[int],
        duration: float = 0.1,
    ) -> 'AnimationClip':
        """Add frames by sprite sheet indices (fluent)."""
        for idx in indices:
            self.add_frame(str(idx), duration)
        return self

    @classmethod
    def from_indices(
        cls,
        name: str,
        indices: List[int],
        frame_duration: float = 0.1,
        loop_mode: LoopMode = LoopMode.LOOP,
    ) -> 'AnimationClip':
        """Create clip from sprite sheet frame indices."""
        clip = cls(name=name, loop_mode=loop_mode)
        clip.add_frames_from_indices(indices, frame_duration)
        return clip


@dataclass
class AnimationSet:
    """
    Collection of animations for an entity.

    An entity typically has multiple clips (idle, walk, attack, etc.)
    organized in an AnimationSet.
    """
    clips: Dict[str, AnimationClip] = field(default_factory=dict)
    default_clip: str = "idle"

    def add_clip(self, clip: AnimationClip) -> 'AnimationSet':
        """Add a clip to the set (fluent)."""
        self.clips[clip.name] = clip
        return self

    def get_clip(self, name: str) -> Optional[AnimationClip]:
        """Get clip by name."""
        return self.clips.get(name)

    def has_clip(self, name: str) -> bool:
        """Check if clip exists."""
        return name in self.clips

    @property
    def clip_names(self) -> List[str]:
        """Get all clip names."""
        return list(self.clips.keys())


class AnimationController:
    """
    Controls animation playback for an entity.

    Handles:
    - Current animation state
    - Transitions between animations
    - Speed control
    - Frame events
    - Playback control (play, pause, stop)
    """

    def __init__(self, animation_set: Optional[AnimationSet] = None):
        self._animation_set = animation_set
        self._current_clip: Optional[AnimationClip] = None
        self._current_time: float = 0.0
        self._playing: bool = True
        self._speed: float = 1.0

        # Callbacks
        self.on_frame_event: Optional[Callable[[str], None]] = None
        self.on_animation_complete: Optional[Callable[[str], None]] = None
        self.on_loop: Optional[Callable[[str], None]] = None

        # State tracking
        self._last_frame_index: int = -1
        self._completed: bool = False

        # Start with default clip if available
        if animation_set and animation_set.default_clip:
            self.play(animation_set.default_clip)

    @property
    def animation_set(self) -> Optional[AnimationSet]:
        """Get the animation set."""
        return self._animation_set

    @animation_set.setter
    def animation_set(self, value: AnimationSet) -> None:
        """Set animation set and reset state."""
        self._animation_set = value
        self._current_clip = None
        self._current_time = 0.0
        self._last_frame_index = -1
        self._completed = False

        if value and value.default_clip:
            self.play(value.default_clip)

    @property
    def current_clip(self) -> Optional[AnimationClip]:
        """Get currently playing clip."""
        return self._current_clip

    @property
    def current_clip_name(self) -> Optional[str]:
        """Get name of current clip."""
        return self._current_clip.name if self._current_clip else None

    @property
    def current_time(self) -> float:
        """Get current playback time."""
        return self._current_time

    @property
    def current_frame(self) -> Optional[AnimationFrame]:
        """Get current animation frame."""
        if not self._current_clip:
            return None
        frame, _ = self._current_clip.get_frame_at_time(self._current_time)
        return frame

    @property
    def current_frame_index(self) -> int:
        """Get current frame index."""
        if not self._current_clip:
            return 0
        _, index = self._current_clip.get_frame_at_time(self._current_time)
        return index

    @property
    def is_playing(self) -> bool:
        """Check if animation is playing."""
        return self._playing

    @property
    def is_complete(self) -> bool:
        """Check if non-looping animation has finished."""
        return self._completed

    @property
    def speed(self) -> float:
        """Get playback speed multiplier."""
        return self._speed

    @speed.setter
    def speed(self, value: float) -> None:
        """Set playback speed multiplier."""
        self._speed = max(0.0, value)

    @property
    def progress(self) -> float:
        """Get animation progress (0-1)."""
        if not self._current_clip or self._current_clip.total_duration <= 0:
            return 0.0
        return min(1.0, self._current_time / self._current_clip.total_duration)

    def play(self, clip_name: str, restart: bool = False) -> bool:
        """
        Play an animation clip.

        Args:
            clip_name: Name of clip to play
            restart: If True, restart even if already playing this clip

        Returns:
            True if clip was found and started
        """
        if not self._animation_set:
            return False

        # Check if already playing this clip
        if not restart and self._current_clip and self._current_clip.name == clip_name:
            return True

        clip = self._animation_set.get_clip(clip_name)
        if not clip:
            return False

        self._current_clip = clip
        self._current_time = 0.0
        self._last_frame_index = -1
        self._playing = True
        self._completed = False

        return True

    def stop(self) -> None:
        """Stop playback and reset to start."""
        self._playing = False
        self._current_time = 0.0
        self._last_frame_index = -1

    def pause(self) -> None:
        """Pause playback at current position."""
        self._playing = False

    def resume(self) -> None:
        """Resume paused playback."""
        self._playing = True

    def set_frame(self, index: int) -> None:
        """Jump to specific frame."""
        if not self._current_clip:
            return

        # Calculate time for frame
        time = 0.0
        for i, frame in enumerate(self._current_clip.frames):
            if i >= index:
                break
            time += frame.duration

        self._current_time = time
        self._last_frame_index = index - 1  # Will trigger event check

    def update(self, dt: float) -> None:
        """
        Advance animation by delta time.

        Args:
            dt: Delta time in seconds
        """
        if not self._playing or not self._current_clip:
            return

        # Apply speed modifiers
        effective_speed = self._speed * self._current_clip.speed_multiplier
        self._current_time += dt * effective_speed

        # Get current frame
        frame, frame_index = self._current_clip.get_frame_at_time(self._current_time)

        # Check for frame change and fire events
        if frame_index != self._last_frame_index:
            if frame.event and self.on_frame_event:
                self.on_frame_event(frame.event)
            self._last_frame_index = frame_index

        # Check for completion/looping
        duration = self._current_clip.total_duration
        if self._current_time >= duration:
            if self._current_clip.loop_mode == LoopMode.ONCE:
                self._playing = False
                self._completed = True
                self._current_time = duration

                if self.on_animation_complete:
                    self.on_animation_complete(self._current_clip.name)
            else:
                # Looping - fire loop callback
                if self.on_loop:
                    self.on_loop(self._current_clip.name)

    def get_frame_offset(self) -> tuple[float, float]:
        """Get current frame's offset values."""
        frame = self.current_frame
        if frame:
            return (frame.offset_x, frame.offset_y)
        return (0.0, 0.0)


# Convenience functions for common animation patterns

def create_directional_animations(
    base_name: str,
    frames_per_direction: int,
    frame_duration: float = 0.1,
    directions: List[str] = None,
) -> AnimationSet:
    """
    Create animations for 4 or 8 directions.

    Assumes sprite sheet layout with rows for each direction.

    Args:
        base_name: Base name (e.g., 'walk' creates 'walk_down', 'walk_up', etc.)
        frames_per_direction: Frames per direction row
        frame_duration: Duration per frame
        directions: Direction names (default: down, left, right, up)

    Returns:
        AnimationSet with directional clips
    """
    if directions is None:
        directions = ['down', 'left', 'right', 'up']

    anim_set = AnimationSet()

    for dir_idx, direction in enumerate(directions):
        clip = AnimationClip(
            name=f"{base_name}_{direction}",
            loop_mode=LoopMode.LOOP,
        )

        start_frame = dir_idx * frames_per_direction
        for i in range(frames_per_direction):
            clip.add_frame(str(start_frame + i), frame_duration)

        anim_set.add_clip(clip)

    # Set default to down
    if f"{base_name}_down" in anim_set.clips:
        anim_set.default_clip = f"{base_name}_down"

    return anim_set
