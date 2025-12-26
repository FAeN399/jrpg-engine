"""
Music player wrapper for pygame.mixer.music.
Handles BGM streaming, transitions, and playlists.
"""

from __future__ import annotations

import logging
import pygame
from typing import Optional


class MusicPlayer:
    """
    Handles background music playback using pygame.mixer.music.
    
    Features:
    - Streaming playback (OGG/MP3/WAV)
    - Volume control
    - Crossfading (fade out then play)
    - Playlist queuing
    - Dynamic layer switching (sync position)
    """

    def __init__(self):
        self._volume: float = 1.0
        self._current_track: str = ""
        self._is_paused: bool = False
        self._playlist: list[str] = []
        
        # State for manual crossfades if needed
        self._fading_out: bool = False
        self._next_track_data: dict | None = None

    @property
    def volume(self) -> float:
        """Get current music volume (0.0 to 1.0)."""
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        """Set music volume."""
        self._volume = max(0.0, min(1.0, value))
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(self._volume)

    @property
    def current_track(self) -> str:
        """Get the currently playing track ID/path."""
        return self._current_track

    def play(self, track_path: str, loops: int = -1, start: float = 0.0, fade_ms: int = 0) -> None:
        """
        Play a music track.
        
        Args:
            track_path: Path to the music file
            loops: Number of loops (-1 for infinite)
            start: Start position in seconds
            fade_ms: Fade in duration in milliseconds
        """
        if not pygame.mixer.get_init():
            logging.warning("Audio system not initialized, cannot play music.")
            return

        try:
            pygame.mixer.music.load(track_path)
            pygame.mixer.music.play(loops=loops, start=start, fade_ms=fade_ms)
            pygame.mixer.music.set_volume(self._volume)
            self._current_track = track_path
            self._is_paused = False
            logging.info(f"Playing BGM: {track_path}")
        except pygame.error as e:
            logging.error(f"Failed to load music '{track_path}': {e}")

    def stop(self, fade_ms: int = 0) -> None:
        """Stop playback."""
        if not pygame.mixer.get_init():
            return
            
        if fade_ms > 0:
            pygame.mixer.music.fadeout(fade_ms)
        else:
            pygame.mixer.music.stop()
        
        # Note: We don't clear _current_track immediately if fading,
        # but for simplicity we consider it 'stopping' logic.

    def pause(self) -> None:
        """Pause playback."""
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self._is_paused = True

    def unpause(self) -> None:
        """Resume playback."""
        if pygame.mixer.get_init() and self._is_paused:
            pygame.mixer.music.unpause()
            self._is_paused = False

    def is_playing(self) -> bool:
        """Check if music is playing."""
        return pygame.mixer.get_init() and pygame.mixer.music.get_busy()

    def crossfade(self, track_path: str, duration_sec: float = 1.0, sync: bool = False) -> None:
        """
        Transition to a new track.
        
        Args:
            track_path: New track file
            duration_sec: Crossfade duration
            sync: If True, maintains current playback position (for layers)
                If False, fade out current -> fade in new
        """
        if not self.is_playing() or not self._current_track:
            self.play(track_path, fade_ms=int(duration_sec * 1000))
            return

        if sync:
            # Immediate switch keeping position (Dynamic Layers)
            # Cannot fade in/out smoothly without 2 channels, so we just switch.
            # Ideally we'd use two channels for smooth layer mixing, but pygame.music is 1-channel.
            try:
                pos = pygame.mixer.music.get_pos() / 1000.0  # ms -> seconds
                self.play(track_path, start=pos, fade_ms=100) # Small fade to de-click
            except pygame.error:
                self.play(track_path)
        else:
            # Standard Crossfade: Fade OUT, then Audio Manager needs to trigger next play
            # Since MusicPlayer is passive, we can implement a 'blocking' play or 
            # we rely on the Manager to handle the 'on end' logic.
            # But here we can use the 'queue' trick if pygame allows or just simple fade-stop-play.
            
            # Simple implementation: stop old with fade, start new.
            # Pygame music doesn't support "crossfade" (overlap) natively.
            # We will use set_endevent logic in Manager, or just restart.
            
            # For now, we'll do a simple swap.
            self.play(track_path, fade_ms=int(duration_sec * 1000))

    def queue(self, track_path: str) -> None:
        """Queue a track to play after current one finishes."""
        if not pygame.mixer.get_init():
            return
        try:
            pygame.mixer.music.queue(track_path)
            self._playlist.append(track_path)
        except pygame.error as e:
            logging.error(f"Failed to queue music '{track_path}': {e}")
