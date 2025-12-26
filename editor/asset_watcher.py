"""
Asset hot reload system for the editor.

Watches asset directories for file changes and triggers reloads.
Uses watchdog library for cross-platform file system monitoring.
"""

from __future__ import annotations

import os
import time
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Set, Optional
from enum import Enum, auto
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from engine.core.events import EventBus

# Try to import watchdog, fall back to polling if not available
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object
    FileSystemEvent = None


class AssetEventType(Enum):
    """Types of asset file events."""
    CREATED = auto()
    MODIFIED = auto()
    DELETED = auto()
    MOVED = auto()


@dataclass
class AssetEvent:
    """
    An asset file change event.

    Attributes:
        event_type: Type of change
        path: Path to the changed file
        old_path: For moves, the original path
        timestamp: When the event occurred
    """
    event_type: AssetEventType
    path: Path
    old_path: Optional[Path] = None
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        """Ensure paths are Path objects."""
        if isinstance(self.path, str):
            self.path = Path(self.path)
        if isinstance(self.old_path, str):
            self.old_path = Path(self.old_path)

    @property
    def extension(self) -> str:
        """Get file extension (lowercase)."""
        return self.path.suffix.lower()

    @property
    def is_image(self) -> bool:
        """Check if this is an image file."""
        return self.extension in {'.png', '.jpg', '.jpeg', '.bmp', '.gif'}

    @property
    def is_audio(self) -> bool:
        """Check if this is an audio file."""
        return self.extension in {'.wav', '.ogg', '.mp3', '.flac'}

    @property
    def is_data(self) -> bool:
        """Check if this is a data file."""
        return self.extension in {'.json', '.yaml', '.yml', '.toml'}


# File extensions to watch
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif'}
AUDIO_EXTENSIONS = {'.wav', '.ogg', '.mp3', '.flac'}
DATA_EXTENSIONS = {'.json', '.yaml', '.yml', '.toml'}
ALL_EXTENSIONS = IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | DATA_EXTENSIONS


class AssetEventHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """
    Handles file system events from watchdog.

    Filters events to only asset files and debounces rapid changes.
    """

    def __init__(
        self,
        callback: Callable[[AssetEvent], None],
        extensions: Set[str] = None,
        debounce_seconds: float = 0.5,
    ):
        if WATCHDOG_AVAILABLE:
            super().__init__()
        self.callback = callback
        self.extensions = extensions or ALL_EXTENSIONS
        self.debounce_seconds = debounce_seconds

        # Debounce tracking
        self._last_events: dict[str, float] = {}
        self._lock = threading.Lock()

    def _should_process(self, path: str) -> bool:
        """Check if this file should be processed."""
        ext = Path(path).suffix.lower()
        if ext not in self.extensions:
            return False

        # Ignore hidden files and temp files
        name = Path(path).name
        if name.startswith('.') or name.startswith('~') or name.endswith('~'):
            return False

        return True

    def _is_debounced(self, path: str) -> bool:
        """Check if this event should be debounced."""
        with self._lock:
            now = time.time()
            last = self._last_events.get(path, 0)

            if now - last < self.debounce_seconds:
                return True

            self._last_events[path] = now
            return False

    def _emit_event(self, event_type: AssetEventType, path: str, old_path: str = None) -> None:
        """Emit an asset event."""
        if not self._should_process(path):
            return

        if self._is_debounced(path):
            return

        event = AssetEvent(
            event_type=event_type,
            path=Path(path),
            old_path=Path(old_path) if old_path else None,
        )

        try:
            self.callback(event)
        except Exception as e:
            print(f"Error in asset event callback: {e}")

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation."""
        if event.is_directory:
            return
        self._emit_event(AssetEventType.CREATED, event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification."""
        if event.is_directory:
            return
        self._emit_event(AssetEventType.MODIFIED, event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion."""
        if event.is_directory:
            return
        self._emit_event(AssetEventType.DELETED, event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move/rename."""
        if event.is_directory:
            return
        self._emit_event(AssetEventType.MOVED, event.dest_path, event.src_path)


class AssetWatcher:
    """
    Watches directories for asset file changes.

    Usage:
        watcher = AssetWatcher()
        watcher.add_callback(on_asset_changed)
        watcher.watch("assets/sprites")
        watcher.start()

        # Later...
        watcher.stop()
    """

    def __init__(self, debounce_seconds: float = 0.5):
        self._debounce = debounce_seconds
        self._callbacks: list[Callable[[AssetEvent], None]] = []
        self._watched_paths: list[Path] = []
        self._running = False

        if WATCHDOG_AVAILABLE:
            self._observer: Optional[Observer] = None
        else:
            self._poll_thread: Optional[threading.Thread] = None
            self._poll_state: dict[str, float] = {}

    @property
    def is_available(self) -> bool:
        """Check if file watching is available."""
        return WATCHDOG_AVAILABLE

    @property
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running

    def add_callback(self, callback: Callable[[AssetEvent], None]) -> None:
        """Add a callback for asset events."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[AssetEvent], None]) -> None:
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def watch(self, path: str | Path, recursive: bool = True) -> bool:
        """
        Add a directory to watch.

        Args:
            path: Directory path to watch
            recursive: Watch subdirectories too

        Returns:
            True if path was added successfully
        """
        path = Path(path)
        if not path.exists() or not path.is_dir():
            print(f"Warning: Cannot watch non-existent directory: {path}")
            return False

        if path not in self._watched_paths:
            self._watched_paths.append(path)

        # If already running, schedule the new path
        if self._running and WATCHDOG_AVAILABLE and self._observer:
            handler = AssetEventHandler(self._dispatch_event, debounce_seconds=self._debounce)
            self._observer.schedule(handler, str(path), recursive=recursive)

        return True

    def _dispatch_event(self, event: AssetEvent) -> None:
        """Dispatch event to all callbacks."""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in asset watcher callback: {e}")

    def start(self) -> bool:
        """
        Start watching for changes.

        Returns:
            True if started successfully
        """
        if self._running:
            return True

        if not self._watched_paths:
            print("Warning: No paths to watch")
            return False

        if WATCHDOG_AVAILABLE:
            return self._start_watchdog()
        else:
            return self._start_polling()

    def _start_watchdog(self) -> bool:
        """Start watching using watchdog."""
        try:
            self._observer = Observer()
            handler = AssetEventHandler(self._dispatch_event, debounce_seconds=self._debounce)

            for path in self._watched_paths:
                self._observer.schedule(handler, str(path), recursive=True)

            self._observer.start()
            self._running = True
            print(f"Asset watcher started (watching {len(self._watched_paths)} paths)")
            return True

        except Exception as e:
            print(f"Failed to start asset watcher: {e}")
            return False

    def _start_polling(self) -> bool:
        """Start watching using polling (fallback)."""
        print("Warning: watchdog not installed, using polling (slower)")

        # Initialize state
        self._poll_state = {}
        for path in self._watched_paths:
            self._scan_directory(path)

        # Start poll thread
        self._running = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        return True

    def _scan_directory(self, path: Path) -> None:
        """Scan directory and record file modification times."""
        for root, dirs, files in os.walk(path):
            for name in files:
                filepath = Path(root) / name
                if filepath.suffix.lower() in ALL_EXTENSIONS:
                    try:
                        self._poll_state[str(filepath)] = filepath.stat().st_mtime
                    except OSError:
                        pass

    def _poll_loop(self) -> None:
        """Polling loop for when watchdog is not available."""
        while self._running:
            time.sleep(1.0)  # Poll every second

            for path in self._watched_paths:
                self._poll_check(path)

    def _poll_check(self, path: Path) -> None:
        """Check a directory for changes (polling mode)."""
        current = {}

        for root, dirs, files in os.walk(path):
            for name in files:
                filepath = Path(root) / name
                if filepath.suffix.lower() not in ALL_EXTENSIONS:
                    continue

                key = str(filepath)
                try:
                    mtime = filepath.stat().st_mtime
                    current[key] = mtime

                    old_mtime = self._poll_state.get(key)
                    if old_mtime is None:
                        # New file
                        self._dispatch_event(AssetEvent(
                            event_type=AssetEventType.CREATED,
                            path=filepath,
                        ))
                    elif mtime > old_mtime:
                        # Modified file
                        self._dispatch_event(AssetEvent(
                            event_type=AssetEventType.MODIFIED,
                            path=filepath,
                        ))

                except OSError:
                    pass

        # Check for deleted files
        for key in list(self._poll_state.keys()):
            if key.startswith(str(path)) and key not in current:
                self._dispatch_event(AssetEvent(
                    event_type=AssetEventType.DELETED,
                    path=Path(key),
                ))

        # Update state
        for key in list(self._poll_state.keys()):
            if key.startswith(str(path)):
                del self._poll_state[key]
        self._poll_state.update(current)

    def stop(self) -> None:
        """Stop watching for changes."""
        if not self._running:
            return

        self._running = False

        if WATCHDOG_AVAILABLE and self._observer:
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._observer = None
        elif self._poll_thread:
            self._poll_thread.join(timeout=2.0)
            self._poll_thread = None

        print("Asset watcher stopped")

    def __enter__(self) -> AssetWatcher:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit."""
        self.stop()
