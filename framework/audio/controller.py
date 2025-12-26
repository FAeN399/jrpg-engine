"""
Game Audio Controller - wires game events to audio playback.

Subscribes to engine/UI/game events and triggers appropriate audio responses.
Handles BGM transitions, UI sounds, and SFX preloading.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Any

from engine.core.events import EventBus, Event, EngineEvent, UIEvent, AudioEvent

if TYPE_CHECKING:
    from engine.audio.manager import AudioManager


class SoundBank(Enum):
    """Predefined sound effect categories."""
    UI_CONFIRM = auto()
    UI_CANCEL = auto()
    UI_CURSOR = auto()
    UI_ERROR = auto()
    MENU_OPEN = auto()
    MENU_CLOSE = auto()
    DIALOG_BLIP = auto()
    DIALOG_CHOICE = auto()
    BATTLE_START = auto()
    BATTLE_VICTORY = auto()
    BATTLE_DEFEAT = auto()
    BATTLE_HIT = auto()
    BATTLE_MISS = auto()
    BATTLE_CRITICAL = auto()
    ITEM_GET = auto()
    QUEST_COMPLETE = auto()
    LEVEL_UP = auto()
    SAVE = auto()
    LOAD = auto()


@dataclass
class SceneBGM:
    """BGM configuration for a scene."""
    track: str
    loop: bool = True
    fade_in_ms: int = 1000
    volume: float = 1.0


@dataclass
class AudioConfig:
    """Complete audio configuration."""
    # Sound effect paths
    sfx: dict[str, str] = field(default_factory=dict)

    # Scene-to-BGM mapping
    scene_bgm: dict[str, SceneBGM] = field(default_factory=dict)

    # Default paths
    sfx_path: str = "game/assets/audio/sfx/"
    bgm_path: str = "game/assets/audio/bgm/"

    # Settings
    default_crossfade_duration: float = 1.0


class GameAudioController:
    """
    Central controller for game audio integration.

    Responsibilities:
    - Subscribe to game events and play appropriate sounds
    - Manage BGM transitions between scenes
    - Preload commonly used sound effects
    - Provide audio settings persistence

    Usage:
        audio_ctrl = GameAudioController(audio_manager, event_bus)
        audio_ctrl.load_config("game/data/audio_config.json")

        # Or configure programmatically
        audio_ctrl.set_sound(SoundBank.UI_CONFIRM, "ui/confirm.ogg")
        audio_ctrl.set_scene_bgm("title", "bgm/title_theme.ogg")
    """

    def __init__(
        self,
        audio_manager: AudioManager,
        event_bus: EventBus,
        config_path: Optional[str] = None,
    ):
        self.audio = audio_manager
        self.event_bus = event_bus
        self.config = AudioConfig()

        # Runtime state
        self._current_scene: str = ""
        self._preloaded_sounds: set[str] = set()
        self._enabled: bool = True

        # Subscribe to events
        self._subscribe_events()

        # Load config if provided
        if config_path:
            self.load_config(config_path)
        else:
            self._setup_default_sounds()

    def _subscribe_events(self) -> None:
        """Subscribe to all relevant game events."""
        bus = self.event_bus

        # UI Events
        bus.subscribe(UIEvent.BUTTON_CLICKED, self._on_button_clicked, weak=False)
        bus.subscribe(UIEvent.MENU_OPENED, self._on_menu_opened, weak=False)
        bus.subscribe(UIEvent.MENU_CLOSED, self._on_menu_closed, weak=False)
        bus.subscribe(UIEvent.SELECTION_CHANGED, self._on_selection_changed, weak=False)
        bus.subscribe(UIEvent.DIALOG_STARTED, self._on_dialog_started, weak=False)
        bus.subscribe(UIEvent.DIALOG_ENDED, self._on_dialog_ended, weak=False)

        # Engine Events
        bus.subscribe(EngineEvent.SCENE_PUSHED, self._on_scene_changed, weak=False)
        bus.subscribe(EngineEvent.SCENE_POPPED, self._on_scene_changed, weak=False)
        bus.subscribe(EngineEvent.SCENE_SWITCHED, self._on_scene_changed, weak=False)
        bus.subscribe(EngineEvent.GAME_PAUSE, self._on_game_pause, weak=False)
        bus.subscribe(EngineEvent.GAME_RESUME, self._on_game_resume, weak=False)

    def _setup_default_sounds(self) -> None:
        """Set up default sound effect mappings."""
        defaults = {
            SoundBank.UI_CONFIRM: "ui/confirm.ogg",
            SoundBank.UI_CANCEL: "ui/cancel.ogg",
            SoundBank.UI_CURSOR: "ui/cursor.ogg",
            SoundBank.UI_ERROR: "ui/error.ogg",
            SoundBank.MENU_OPEN: "ui/menu_open.ogg",
            SoundBank.MENU_CLOSE: "ui/menu_close.ogg",
            SoundBank.DIALOG_BLIP: "ui/text_blip.ogg",
            SoundBank.DIALOG_CHOICE: "ui/choice_select.ogg",
            SoundBank.BATTLE_START: "battle/start.ogg",
            SoundBank.BATTLE_VICTORY: "battle/victory.ogg",
            SoundBank.BATTLE_DEFEAT: "battle/defeat.ogg",
            SoundBank.BATTLE_HIT: "battle/hit.ogg",
            SoundBank.BATTLE_MISS: "battle/miss.ogg",
            SoundBank.BATTLE_CRITICAL: "battle/critical.ogg",
            SoundBank.ITEM_GET: "system/item_get.ogg",
            SoundBank.QUEST_COMPLETE: "system/quest_complete.ogg",
            SoundBank.LEVEL_UP: "system/level_up.ogg",
            SoundBank.SAVE: "system/save.ogg",
            SoundBank.LOAD: "system/load.ogg",
        }

        for bank, path in defaults.items():
            self.config.sfx[bank.name] = path

    # Configuration

    def load_config(self, path: str) -> bool:
        """
        Load audio configuration from JSON file.

        Expected format:
        {
            "sfx_path": "game/assets/audio/sfx/",
            "bgm_path": "game/assets/audio/bgm/",
            "sounds": {
                "UI_CONFIRM": "ui/confirm.ogg",
                ...
            },
            "scene_bgm": {
                "title": {"track": "title_theme.ogg", "loop": true},
                "battle": {"track": "battle.ogg", "fade_in_ms": 500}
            }
        }
        """
        config_file = Path(path)
        if not config_file.exists():
            return False

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.config.sfx_path = data.get("sfx_path", self.config.sfx_path)
            self.config.bgm_path = data.get("bgm_path", self.config.bgm_path)

            # Load sound mappings
            for name, path in data.get("sounds", {}).items():
                self.config.sfx[name] = path

            # Load scene BGM
            for scene, bgm_data in data.get("scene_bgm", {}).items():
                if isinstance(bgm_data, str):
                    self.config.scene_bgm[scene] = SceneBGM(track=bgm_data)
                else:
                    self.config.scene_bgm[scene] = SceneBGM(
                        track=bgm_data["track"],
                        loop=bgm_data.get("loop", True),
                        fade_in_ms=bgm_data.get("fade_in_ms", 1000),
                        volume=bgm_data.get("volume", 1.0),
                    )

            return True
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading audio config: {e}")
            return False

    def save_config(self, path: str) -> bool:
        """Save current audio configuration to JSON."""
        data = {
            "sfx_path": self.config.sfx_path,
            "bgm_path": self.config.bgm_path,
            "sounds": self.config.sfx,
            "scene_bgm": {
                scene: {
                    "track": bgm.track,
                    "loop": bgm.loop,
                    "fade_in_ms": bgm.fade_in_ms,
                    "volume": bgm.volume,
                }
                for scene, bgm in self.config.scene_bgm.items()
            },
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except IOError as e:
            print(f"Error saving audio config: {e}")
            return False

    def set_sound(self, bank: SoundBank, path: str) -> None:
        """Set the sound file for a sound bank entry."""
        self.config.sfx[bank.name] = path

    def set_scene_bgm(
        self,
        scene_name: str,
        track: str,
        loop: bool = True,
        fade_in_ms: int = 1000,
    ) -> None:
        """Set the BGM for a scene."""
        self.config.scene_bgm[scene_name] = SceneBGM(
            track=track,
            loop=loop,
            fade_in_ms=fade_in_ms,
        )

    # Sound playback

    def play_sound(
        self,
        bank: SoundBank,
        volume: float = 1.0,
        category: str = "sfx",
    ) -> bool:
        """
        Play a sound from the sound bank.

        Returns:
            True if sound was played successfully
        """
        if not self._enabled:
            return False

        path = self.config.sfx.get(bank.name)
        if not path:
            return False

        full_path = self.config.sfx_path + path
        channel = self.audio.play_sfx(full_path, category=category, volume=volume)
        return channel is not None

    def play_sfx(self, filename: str, volume: float = 1.0, category: str = "sfx") -> bool:
        """Play a sound effect by filename."""
        if not self._enabled:
            return False

        full_path = self.config.sfx_path + filename
        channel = self.audio.play_sfx(full_path, category=category, volume=volume)
        return channel is not None

    def play_bgm(
        self,
        track: str,
        loop: bool = True,
        crossfade: bool = True,
    ) -> None:
        """Play background music."""
        full_path = self.config.bgm_path + track

        if crossfade and self.audio.music.is_playing():
            self.audio.crossfade_bgm(full_path, self.config.default_crossfade_duration)
        else:
            self.audio.play_bgm(full_path, loop=loop)

    def stop_bgm(self, fade_ms: int = 1000) -> None:
        """Stop background music."""
        self.audio.stop_bgm(fade_ms)

    # Preloading

    def preload_sounds(self, banks: list[SoundBank]) -> int:
        """
        Preload sounds into cache for faster playback.

        Returns:
            Number of sounds preloaded
        """
        count = 0
        for bank in banks:
            path = self.config.sfx.get(bank.name)
            if path:
                full_path = self.config.sfx_path + path
                # AudioManager._get_sound caches sounds
                if self.audio._get_sound(full_path):
                    self._preloaded_sounds.add(bank.name)
                    count += 1
        return count

    def preload_ui_sounds(self) -> int:
        """Preload all UI-related sounds."""
        ui_banks = [
            SoundBank.UI_CONFIRM,
            SoundBank.UI_CANCEL,
            SoundBank.UI_CURSOR,
            SoundBank.UI_ERROR,
            SoundBank.MENU_OPEN,
            SoundBank.MENU_CLOSE,
            SoundBank.DIALOG_BLIP,
            SoundBank.DIALOG_CHOICE,
        ]
        return self.preload_sounds(ui_banks)

    def preload_battle_sounds(self) -> int:
        """Preload all battle-related sounds."""
        battle_banks = [
            SoundBank.BATTLE_START,
            SoundBank.BATTLE_VICTORY,
            SoundBank.BATTLE_DEFEAT,
            SoundBank.BATTLE_HIT,
            SoundBank.BATTLE_MISS,
            SoundBank.BATTLE_CRITICAL,
        ]
        return self.preload_sounds(battle_banks)

    # Event handlers

    def _on_button_clicked(self, event: Event) -> None:
        """Handle UI button click."""
        self.play_sound(SoundBank.UI_CONFIRM, category="ui")

    def _on_menu_opened(self, event: Event) -> None:
        """Handle menu opened."""
        self.play_sound(SoundBank.MENU_OPEN, category="ui")

    def _on_menu_closed(self, event: Event) -> None:
        """Handle menu closed."""
        self.play_sound(SoundBank.MENU_CLOSE, category="ui")

    def _on_selection_changed(self, event: Event) -> None:
        """Handle selection cursor movement."""
        self.play_sound(SoundBank.UI_CURSOR, category="ui", volume=0.5)

    def _on_dialog_started(self, event: Event) -> None:
        """Handle dialog starting."""
        # Could play a dialog start sound or lower BGM volume
        pass

    def _on_dialog_ended(self, event: Event) -> None:
        """Handle dialog ending."""
        pass

    def _on_scene_changed(self, event: Event) -> None:
        """Handle scene transitions - update BGM."""
        scene_name = event.get("scene_name", "")
        if not scene_name:
            return

        self._current_scene = scene_name

        # Check if this scene has configured BGM
        bgm = self.config.scene_bgm.get(scene_name)
        if bgm:
            full_path = self.config.bgm_path + bgm.track
            if self.audio.music.current_track != full_path:
                self.audio.crossfade_bgm(
                    full_path,
                    duration=self.config.default_crossfade_duration,
                )

    def _on_game_pause(self, event: Event) -> None:
        """Handle game pause - pause BGM."""
        self.audio.music.pause()

    def _on_game_resume(self, event: Event) -> None:
        """Handle game resume - unpause BGM."""
        self.audio.music.unpause()

    # Battle-specific methods (called directly, not via events)

    def on_battle_start(self, battle_bgm: Optional[str] = None) -> None:
        """Called when battle starts."""
        self.play_sound(SoundBank.BATTLE_START)

        if battle_bgm:
            self.play_bgm(battle_bgm, crossfade=True)

    def on_battle_end(self, victory: bool, restore_bgm: bool = True) -> None:
        """Called when battle ends."""
        if victory:
            self.play_sound(SoundBank.BATTLE_VICTORY)
        else:
            self.play_sound(SoundBank.BATTLE_DEFEAT)

        # Restore previous scene BGM
        if restore_bgm and self._current_scene:
            bgm = self.config.scene_bgm.get(self._current_scene)
            if bgm:
                self.play_bgm(bgm.track, crossfade=True)

    def on_hit(self, is_critical: bool = False) -> None:
        """Play hit sound effect."""
        if is_critical:
            self.play_sound(SoundBank.BATTLE_CRITICAL)
        else:
            self.play_sound(SoundBank.BATTLE_HIT)

    def on_miss(self) -> None:
        """Play miss sound effect."""
        self.play_sound(SoundBank.BATTLE_MISS)

    # Text blip for dialog

    def play_text_blip(self, pitch: float = 1.0) -> None:
        """Play text blip sound for typewriter effect."""
        self.play_sound(SoundBank.DIALOG_BLIP, category="ui", volume=0.3)

    # Settings persistence

    def get_volume_settings(self) -> dict[str, float]:
        """Get current volume settings."""
        return self.audio.get_settings()

    def apply_volume_settings(self, settings: dict) -> None:
        """Apply volume settings."""
        self.audio.apply_settings(settings)

    def save_settings(self, path: str) -> bool:
        """Save volume settings to JSON file."""
        settings = self.audio.get_settings()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
            return True
        except IOError:
            return False

    def load_settings(self, path: str) -> bool:
        """Load volume settings from JSON file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                settings = json.load(f)
            self.audio.apply_settings(settings)
            return True
        except (IOError, json.JSONDecodeError):
            return False

    # Enable/disable

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable audio controller."""
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        """Check if audio controller is enabled."""
        return self._enabled
