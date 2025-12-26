"""
Core Audio Manager.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path

import pygame

from engine.audio.music import MusicPlayer
from engine.core.events import EventBus, AudioEvent


class AudioManager:
    """
    Central audio manager for the engine.
    
    Handles:
    - BGM via MusicPlayer
    - SFX caching and playback
    - Spatial audio calculations
    - Volume categories (Master, BGM, SFX, etc.)
    """

    def __init__(self, event_bus: EventBus | None = None):
        self.music = MusicPlayer()
        self.event_bus = event_bus
        
        # Configuration
        self._master_volume: float = 1.0
        self._category_volumes: dict[str, float] = {
            "bgm": 1.0,
            "sfx": 1.0,
            "ui": 1.0,
            "voice": 1.0,
            "ambient": 1.0
        }
        
        # Resources
        self._sound_cache: dict[str, pygame.mixer.Sound] = {}
        
        # State
        self._listener_pos: tuple[float, float] = (0.0, 0.0)
        self._initialized: bool = False

    def init(self, frequency: int = 44100, size: int = -16, channels: int = 2, buffer: int = 512) -> None:
        """Initialize the audio system."""
        if pygame.mixer.get_init():
            return
            
        try:
            pygame.mixer.init(frequency=frequency, size=size, channels=channels, buffer=buffer)
            pygame.mixer.set_num_channels(32)  # Allocate plenty of channels
            self._initialized = True
            logging.info("Audio system initialized.")
        except pygame.error as e:
            logging.error(f"Failed to initialize audio system: {e}")

    def quit(self) -> None:
        """Shutdown audio system."""
        pygame.mixer.quit()
        self._initialized = False

    # --- Volume Control ---

    def set_master_volume(self, volume: float) -> None:
        """Set master volume (0.0 to 1.0)."""
        self._master_volume = max(0.0, min(1.0, volume))
        self._update_music_volume()

    def set_category_volume(self, category: str, volume: float) -> None:
        """Set volume for a specific category."""
        if category in self._category_volumes:
            self._category_volumes[category] = max(0.0, min(1.0, volume))
            if category == "bgm":
                self._update_music_volume()

    def _update_music_volume(self) -> None:
        """Update music player volume based on master * bgm."""
        vol = self._master_volume * self._category_volumes.get("bgm", 1.0)
        self.music.volume = vol

    def get_settings(self) -> dict:
        """Get all volume settings."""
        return {
            "master": self._master_volume,
            "categories": self._category_volumes.copy()
        }

    def apply_settings(self, settings: dict) -> None:
        """Apply volume settings."""
        self.set_master_volume(settings.get("master", 1.0))
        for cat, vol in settings.get("categories", {}).items():
            self.set_category_volume(cat, vol)

    # --- BGM wrappers ---

    def play_bgm(self, file_path: str, loop: bool = True, fade_ms: int = 1000) -> None:
        """Play background music."""
        loops = -1 if loop else 0
        self.music.play(file_path, loops=loops, fade_ms=fade_ms)
        if self.event_bus:
            self.event_bus.publish(AudioEvent.BGM_STARTED, file=file_path)

    def crossfade_bgm(self, file_path: str, duration: float = 1.0) -> None:
        """Crossfade to new track."""
        self.music.crossfade(file_path, duration_sec=duration)
        if self.event_bus:
            self.event_bus.publish(AudioEvent.BGM_CROSSFADE, file=file_path)

    def stop_bgm(self, fade_ms: int = 1000) -> None:
        """Stop background music."""
        self.music.stop(fade_ms=fade_ms)
        if self.event_bus:
            self.event_bus.publish(AudioEvent.BGM_STOPPED)

    # --- SFX ---

    def _get_sound(self, file_path: str) -> pygame.mixer.Sound | None:
        """Load or retrieve sound from cache."""
        if not self._initialized:
            return None
            
        if file_path not in self._sound_cache:
            try:
                if not Path(file_path).exists():
                    logging.warning(f"Audio file not found: {file_path}")
                    return None
                sound = pygame.mixer.Sound(file_path)
                self._sound_cache[file_path] = sound
            except pygame.error as e:
                logging.error(f"Failed to load sound {file_path}: {e}")
                return None
                
        return self._sound_cache[file_path]

    def play_sfx(
        self, 
        file_path: str, 
        position: tuple[float, float] | None = None,
        category: str = "sfx",
        volume: float = 1.0,
        loops: int = 0
    ) -> pygame.mixer.Channel | None:
        """
        Play a sound effect.
        
        Args:
            file_path: Sound file path
            position: World position (x, y) for spatial audio
            category: Sound category
            volume: Base volume multiplier
            loops: Number of loops
            
        Returns:
            The channel used, or None if failed.
        """
        sound = self._get_sound(file_path)
        if not sound:
            return None

        # Calculate final volume
        cat_vol = self._category_volumes.get(category, 1.0)
        final_vol = self._master_volume * cat_vol * volume

        # Find a channel
        channel = pygame.mixer.find_channel()
        if not channel:
            # Try to force a channel if all busy (rare with 32 channels)
            channel = pygame.mixer.find_channel(True) 
        
        if not channel:
            return None

        # Spatial Audio
        if position and self._listener_pos:
            l_vol, r_vol = self._calculate_spatial_volume(position, self._listener_pos)
            channel.set_volume(final_vol * l_vol, final_vol * r_vol)
        else:
            channel.set_volume(final_vol)

        channel.play(sound, loops=loops)
        
        if self.event_bus:
            self.event_bus.publish(AudioEvent.SFX_PLAYED, file=file_path)
            
        return channel

    def set_listener_position(self, pos: tuple[float, float]) -> None:
        """Update the listener position (e.g. from camera/player)."""
        self._listener_pos = pos

    def _calculate_spatial_volume(self, source_pos: tuple[float, float], listener_pos: tuple[float, float], max_dist: float = 500.0) -> tuple[float, float]:
        """
        Calculate stereo volume based on position.
        
        Returns:
            (left_volume, right_volume)
        """
        dx = source_pos[0] - listener_pos[0]
        dy = source_pos[1] - listener_pos[1]
        
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > max_dist:
            return (0.0, 0.0)
        
        # Attenuation (Linear falloff)
        falloff = 1.0 - (dist / max_dist)
        
        # Panning
        # Simple panning: dx < 0 is left, dx > 0 is right
        # Normalize dx rel to some 'hearing range' for panning width
        # Let's say +/- 300 pixels is full pan opacity
        pan_width = 300.0
        pan = max(-1.0, min(1.0, dx / pan_width))
        
        # pan -1 (Left) -> L=1, R=0
        # pan 0 (Center) -> L=1, R=1 (or 0.7 depending on pan law, using simple linear here)
        # pan 1 (Right) -> L=0, R=1
        
        # Constant power panning (approx)
        angle = (pan + 1.0) * (math.pi / 4.0) # 0 to pi/2
        
        # Simple linear implementation
        # left = (1.0 - pan) / 2  -> No, that's not right.
        
        # Let's use simple balance
        # If pan is -1: L=1, R=0
        # If pan is 0: L=1, R=1
        # If pan is 1: L=0, R=1
        
        left_pan = 1.0 if pan <= 0 else 1.0 - pan
        right_pan = 1.0 if pan >= 0 else 1.0 + pan
        
        return (left_pan * falloff, right_pan * falloff)
