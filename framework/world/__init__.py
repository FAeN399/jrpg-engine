"""
World module - maps, entities, spawning.

Provides:
- Map loading from Tiled format
- Player entity factory
- NPC entity factory
- Map collision and transitions
"""

from framework.world.map import (
    GameMap,
    MapManager,
    MapLayer,
    MapTile,
    MapTileset,
    SpawnPoint,
    MapTransition,
    TileProperty,
)
from framework.world.player import (
    PlayerController,
    create_player,
    create_party_member,
)
from framework.world.npc import (
    create_npc,
    create_patrol_npc,
    create_enemy,
    create_shopkeeper,
    create_sign,
)

__all__ = [
    # Map
    "GameMap",
    "MapManager",
    "MapLayer",
    "MapTile",
    "MapTileset",
    "SpawnPoint",
    "MapTransition",
    "TileProperty",
    # Player
    "PlayerController",
    "create_player",
    "create_party_member",
    # NPC
    "create_npc",
    "create_patrol_npc",
    "create_enemy",
    "create_shopkeeper",
    "create_sign",
]
