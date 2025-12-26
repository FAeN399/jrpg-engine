"""
Save module - game state persistence.

Provides:
- Save/load game state
- Multiple save slots (10 by default)
- Auto-save functionality
- Save metadata (playtime, location, level)
- Checksum validation
- Game flags for progression
"""

from framework.save.manager import (
    SaveManager,
    SaveMetadata,
    PlayerSaveData,
    InventorySaveData,
    GameSaveData,
    SaveEvent,
)

__all__ = [
    "SaveManager",
    "SaveMetadata",
    "PlayerSaveData",
    "InventorySaveData",
    "GameSaveData",
    "SaveEvent",
]
