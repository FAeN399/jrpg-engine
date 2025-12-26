"""
Animation loading and management utilities.

Handles loading animation definitions from JSON files
and managing animation resources.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from engine.graphics.animation import (
    AnimationFrame,
    AnimationClip,
    AnimationSet,
    LoopMode,
)

if TYPE_CHECKING:
    from engine.graphics.texture import TextureAtlas


class AnimationLoader:
    """
    Loads animation definitions from JSON files.

    JSON Format:
    {
        "atlas": "sprites/hero.png",
        "frame_width": 32,
        "frame_height": 32,
        "animations": {
            "idle_down": {
                "frames": [0, 1, 2, 1],
                "frame_duration": 0.2,
                "loop": true
            },
            "walk_down": {
                "frames": [3, 4, 5, 4],
                "frame_duration": 0.1,
                "loop": true
            },
            "attack_down": {
                "frames": [6, 7, 8, 9],
                "frame_duration": 0.08,
                "loop": false,
                "events": {
                    "2": "attack_hit"
                }
            }
        }
    }
    """

    def __init__(self, base_path: str = ""):
        self.base_path = Path(base_path)
        self._cache: Dict[str, AnimationSet] = {}

    def load(self, path: str) -> AnimationSet:
        """
        Load animation set from JSON file.

        Args:
            path: Path to JSON file (relative to base_path)

        Returns:
            AnimationSet with all defined clips
        """
        # Check cache
        cache_key = str(path)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Load JSON
        full_path = self.base_path / path if self.base_path else Path(path)

        with open(full_path, 'r') as f:
            data = json.load(f)

        # Parse animations
        anim_set = self._parse_animation_data(data)

        # Cache result
        self._cache[cache_key] = anim_set

        return anim_set

    def load_from_dict(self, data: Dict[str, Any]) -> AnimationSet:
        """
        Load animation set from dictionary data.

        Args:
            data: Animation definition dictionary

        Returns:
            AnimationSet with all defined clips
        """
        return self._parse_animation_data(data)

    def _parse_animation_data(self, data: Dict[str, Any]) -> AnimationSet:
        """Parse animation data into AnimationSet."""
        anim_set = AnimationSet()

        # Get default settings
        default_duration = data.get('frame_duration', 0.1)
        default_loop = data.get('loop', True)

        # Parse each animation
        animations = data.get('animations', {})

        for name, anim_data in animations.items():
            clip = self._parse_clip(name, anim_data, default_duration, default_loop)
            anim_set.add_clip(clip)

        # Set default clip
        if 'default' in data:
            anim_set.default_clip = data['default']
        elif 'idle_down' in anim_set.clips:
            anim_set.default_clip = 'idle_down'
        elif 'idle' in anim_set.clips:
            anim_set.default_clip = 'idle'
        elif anim_set.clips:
            anim_set.default_clip = next(iter(anim_set.clips.keys()))

        return anim_set

    def _parse_clip(
        self,
        name: str,
        data: Dict[str, Any],
        default_duration: float,
        default_loop: bool,
    ) -> AnimationClip:
        """Parse a single animation clip."""
        # Get loop mode
        loop_value = data.get('loop', default_loop)
        if isinstance(loop_value, str):
            loop_mode = {
                'once': LoopMode.ONCE,
                'loop': LoopMode.LOOP,
                'ping_pong': LoopMode.PING_PONG,
                'pingpong': LoopMode.PING_PONG,
            }.get(loop_value.lower(), LoopMode.LOOP)
        else:
            loop_mode = LoopMode.LOOP if loop_value else LoopMode.ONCE

        clip = AnimationClip(
            name=name,
            loop_mode=loop_mode,
            speed_multiplier=data.get('speed', 1.0),
        )

        # Get frame duration
        frame_duration = data.get('frame_duration', default_duration)

        # Get frame events
        events = data.get('events', {})

        # Parse frames
        frames_data = data.get('frames', [])

        if isinstance(frames_data, list):
            # Simple list of frame indices
            for i, frame_id in enumerate(frames_data):
                event = events.get(str(i))
                clip.add_frame(
                    region_name=str(frame_id),
                    duration=frame_duration,
                    event=event,
                )
        elif isinstance(frames_data, dict):
            # Detailed frame definitions
            for frame_id, frame_data in frames_data.items():
                if isinstance(frame_data, dict):
                    clip.add_frame(
                        region_name=str(frame_data.get('region', frame_id)),
                        duration=frame_data.get('duration', frame_duration),
                        offset_x=frame_data.get('offset_x', 0.0),
                        offset_y=frame_data.get('offset_y', 0.0),
                        event=frame_data.get('event'),
                    )
                else:
                    clip.add_frame(str(frame_id), frame_duration)

        return clip

    def clear_cache(self) -> None:
        """Clear the animation cache."""
        self._cache.clear()


class AnimationManager:
    """
    Manages animation resources for the game.

    Provides:
    - Animation loading with caching
    - Sprite sheet region generation
    - Animation state management
    """

    def __init__(self, base_path: str = ""):
        self._loader = AnimationLoader(base_path)
        self._animation_sets: Dict[str, AnimationSet] = {}

    def load(self, name: str, path: str) -> AnimationSet:
        """
        Load and register an animation set.

        Args:
            name: Name to register animation set under
            path: Path to animation JSON file

        Returns:
            Loaded AnimationSet
        """
        anim_set = self._loader.load(path)
        self._animation_sets[name] = anim_set
        return anim_set

    def get(self, name: str) -> Optional[AnimationSet]:
        """Get a registered animation set by name."""
        return self._animation_sets.get(name)

    def create(self, name: str) -> AnimationSet:
        """
        Create and register a new empty animation set.

        Args:
            name: Name to register animation set under

        Returns:
            New empty AnimationSet
        """
        anim_set = AnimationSet()
        self._animation_sets[name] = anim_set
        return anim_set

    def register(self, name: str, anim_set: AnimationSet) -> None:
        """Register an existing animation set."""
        self._animation_sets[name] = anim_set

    def unload(self, name: str) -> bool:
        """
        Unload an animation set.

        Returns:
            True if animation was found and removed
        """
        if name in self._animation_sets:
            del self._animation_sets[name]
            return True
        return False

    def clear(self) -> None:
        """Unload all animation sets."""
        self._animation_sets.clear()
        self._loader.clear_cache()


def generate_grid_regions(
    atlas_width: int,
    atlas_height: int,
    frame_width: int,
    frame_height: int,
    padding: int = 0,
    margin: int = 0,
) -> List[tuple[int, int, int, int]]:
    """
    Generate frame regions for a grid-based sprite sheet.

    Args:
        atlas_width: Total width of sprite sheet
        atlas_height: Total height of sprite sheet
        frame_width: Width of each frame
        frame_height: Height of each frame
        padding: Padding between frames
        margin: Margin around edges

    Returns:
        List of (x, y, width, height) tuples for each frame
    """
    regions = []

    cell_width = frame_width + padding
    cell_height = frame_height + padding

    cols = (atlas_width - margin * 2 + padding) // cell_width
    rows = (atlas_height - margin * 2 + padding) // cell_height

    for row in range(rows):
        for col in range(cols):
            x = margin + col * cell_width
            y = margin + row * cell_height
            regions.append((x, y, frame_width, frame_height))

    return regions
