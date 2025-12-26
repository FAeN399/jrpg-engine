"""
Save module - game state persistence.

Provides:
- Save/load game state
- Multiple save slots
- Save metadata (playtime, location, level)
- Game flags for progression
"""

from framework.save.manager import (
    SaveManager,
    SaveMetadata,
    PlayerSaveData,
    InventorySaveData,
    GameSaveData,
)

__all__ = [
    "SaveManager",
    "SaveMetadata",
    "PlayerSaveData",
    "InventorySaveData",
    "GameSaveData",
]
