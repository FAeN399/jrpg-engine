"""
Save/Load system - game state persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import TYPE_CHECKING, Optional, Any
from pathlib import Path
from datetime import datetime
import json
import hashlib

from engine.core import World, Entity
from framework.components import (
    Transform,
    Health,
    Mana,
    CharacterStats,
    Experience,
    Inventory,
    Equipment,
)

if TYPE_CHECKING:
    from framework.world.map import MapManager
    from framework.progression.quests import QuestManager


@dataclass
class SaveMetadata:
    """Metadata about a save file."""
    slot: int
    name: str
    timestamp: str
    playtime_seconds: int
    location: str
    level: int
    chapter: str = ""
    screenshot_path: Optional[str] = None


@dataclass
class PlayerSaveData:
    """Saved data for a player/party member."""
    entity_id: int
    name: str
    x: float
    y: float
    facing: str
    hp: int
    max_hp: int
    mp: int
    max_mp: int
    level: int
    exp: int
    exp_total: int
    stats: dict[str, int]
    skills: list[str]
    equipment: dict[str, Optional[str]]


@dataclass
class InventorySaveData:
    """Saved inventory data."""
    gold: int
    items: list[dict[str, Any]]  # [{item_id, quantity}, ...]


@dataclass
class GameSaveData:
    """Complete game save data."""
    version: str = "1.0"
    metadata: SaveMetadata = None
    player: PlayerSaveData = None
    party: list[PlayerSaveData] = field(default_factory=list)
    inventory: InventorySaveData = None
    current_map: str = ""
    quests: dict = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)
    custom_data: dict[str, Any] = field(default_factory=dict)


class SaveManager:
    """
    Manages saving and loading game state.
    """

    VERSION = "1.0"
    MAX_SLOTS = 10

    def __init__(
        self,
        save_path: str = "game/saves",
        world: Optional[World] = None,
    ):
        self.save_path = Path(save_path)
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.world = world

        # External managers (set by game)
        self.quest_manager: Optional[QuestManager] = None
        self.map_manager: Optional[MapManager] = None

        # Runtime tracking
        self._playtime: int = 0  # Seconds
        self._current_slot: Optional[int] = None

        # Game flags (for story progression, switches, etc.)
        self._flags: dict[str, Any] = {}

    def set_world(self, world: World) -> None:
        """Set the world reference."""
        self.world = world

    def set_quest_manager(self, manager: QuestManager) -> None:
        """Set the quest manager."""
        self.quest_manager = manager

    def set_map_manager(self, manager: MapManager) -> None:
        """Set the map manager."""
        self.map_manager = manager

    def update_playtime(self, dt: float) -> None:
        """Update playtime counter."""
        self._playtime += int(dt)

    def get_flag(self, key: str, default: Any = None) -> Any:
        """Get a game flag."""
        return self._flags.get(key, default)

    def set_flag(self, key: str, value: Any) -> None:
        """Set a game flag."""
        self._flags[key] = value

    def _get_slot_path(self, slot: int) -> Path:
        """Get path for a save slot."""
        return self.save_path / f"save_{slot:02d}.json"

    def _get_metadata_path(self, slot: int) -> Path:
        """Get path for save metadata."""
        return self.save_path / f"save_{slot:02d}_meta.json"

    def get_save_slots(self) -> list[Optional[SaveMetadata]]:
        """Get metadata for all save slots."""
        slots = []
        for i in range(self.MAX_SLOTS):
            meta_path = self._get_metadata_path(i)
            if meta_path.exists():
                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    slots.append(SaveMetadata(**data))
                except Exception:
                    slots.append(None)
            else:
                slots.append(None)
        return slots

    def save_game(
        self,
        slot: int,
        name: str = "Save",
        custom_data: Optional[dict] = None,
    ) -> bool:
        """
        Save the current game state.

        Args:
            slot: Save slot number (0-9)
            name: Display name for the save
            custom_data: Additional data to save

        Returns:
            True if save was successful
        """
        if not self.world:
            return False

        try:
            # Create save data
            save_data = self._create_save_data(slot, name)
            if custom_data:
                save_data.custom_data = custom_data

            # Serialize
            save_dict = self._serialize_save_data(save_data)

            # Write save file
            save_path = self._get_slot_path(slot)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(save_dict, f, indent=2)

            # Write metadata
            meta_path = self._get_metadata_path(slot)
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(save_data.metadata), f, indent=2)

            self._current_slot = slot
            return True

        except Exception as e:
            print(f"Save failed: {e}")
            return False

    def load_game(self, slot: int) -> bool:
        """
        Load a saved game.

        Args:
            slot: Save slot number

        Returns:
            True if load was successful
        """
        save_path = self._get_slot_path(slot)
        if not save_path.exists():
            return False

        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                save_dict = json.load(f)

            save_data = self._deserialize_save_data(save_dict)
            self._apply_save_data(save_data)

            self._current_slot = slot
            return True

        except Exception as e:
            print(f"Load failed: {e}")
            return False

    def delete_save(self, slot: int) -> bool:
        """Delete a save slot."""
        try:
            save_path = self._get_slot_path(slot)
            meta_path = self._get_metadata_path(slot)

            if save_path.exists():
                save_path.unlink()
            if meta_path.exists():
                meta_path.unlink()

            return True
        except Exception:
            return False

    def _create_save_data(self, slot: int, name: str) -> GameSaveData:
        """Create save data from current game state."""
        save_data = GameSaveData(version=self.VERSION)

        # Get player entity
        player = None
        for entity_id in self.world.get_entities_with_components(Transform):
            entity = self.world.get_entity(entity_id)
            if entity and "player" in entity.tags:
                player = entity
                break

        # Metadata
        location = ""
        if self.map_manager and self.map_manager.current_map:
            location = self.map_manager.current_map.name

        player_level = 1
        if player:
            exp = player.get(Experience)
            if exp:
                player_level = exp.level

        save_data.metadata = SaveMetadata(
            slot=slot,
            name=name,
            timestamp=datetime.now().isoformat(),
            playtime_seconds=self._playtime,
            location=location,
            level=player_level,
        )

        # Player data
        if player:
            save_data.player = self._create_player_save_data(player)

        # Party members
        for entity_id in self.world.get_entities_with_components(Transform):
            entity = self.world.get_entity(entity_id)
            if entity and "party_member" in entity.tags:
                save_data.party.append(self._create_player_save_data(entity))

        # Inventory
        if player:
            inv = player.get(Inventory)
            if inv:
                save_data.inventory = InventorySaveData(
                    gold=inv.gold,
                    items=[
                        {'item_id': s.item_id, 'quantity': s.quantity}
                        for s in inv.slots if s
                    ],
                )

        # Current map
        if self.map_manager and self.map_manager.current_map:
            save_data.current_map = self.map_manager.current_map.name

        # Quests
        if self.quest_manager:
            save_data.quests = self.quest_manager.get_save_data()

        # Flags
        save_data.flags = self._flags.copy()

        return save_data

    def _create_player_save_data(self, entity: Entity) -> PlayerSaveData:
        """Create save data for a player/party member."""
        transform = entity.get(Transform)
        health = entity.get(Health)
        mana = entity.get(Mana)
        stats = entity.get(CharacterStats)
        exp = entity.get(Experience)
        equipment = entity.get(Equipment)

        return PlayerSaveData(
            entity_id=entity.id,
            name=entity.name,
            x=transform.x if transform else 0,
            y=transform.y if transform else 0,
            facing=transform.facing.name if transform else "DOWN",
            hp=health.current if health else 100,
            max_hp=health.max_hp if health else 100,
            mp=mana.current if mana else 0,
            max_mp=mana.max_mp if mana else 0,
            level=exp.level if exp else 1,
            exp=exp.current if exp else 0,
            exp_total=exp.total if exp else 0,
            stats={
                'strength': stats.strength if stats else 10,
                'defense': stats.defense if stats else 10,
                'magic': stats.magic if stats else 10,
                'resistance': stats.resistance if stats else 10,
                'agility': stats.agility if stats else 10,
                'luck': stats.luck if stats else 10,
            },
            skills=[],  # TODO: Get from skill component
            equipment={
                slot.name: item_id
                for slot, item_id in (equipment.slots.items() if equipment else {})
            },
        )

    def _serialize_save_data(self, save_data: GameSaveData) -> dict:
        """Serialize save data to dictionary."""
        return {
            'version': save_data.version,
            'metadata': asdict(save_data.metadata) if save_data.metadata else None,
            'player': asdict(save_data.player) if save_data.player else None,
            'party': [asdict(p) for p in save_data.party],
            'inventory': asdict(save_data.inventory) if save_data.inventory else None,
            'current_map': save_data.current_map,
            'quests': save_data.quests,
            'flags': save_data.flags,
            'custom_data': save_data.custom_data,
        }

    def _deserialize_save_data(self, data: dict) -> GameSaveData:
        """Deserialize save data from dictionary."""
        save_data = GameSaveData(version=data.get('version', '1.0'))

        if data.get('metadata'):
            save_data.metadata = SaveMetadata(**data['metadata'])

        if data.get('player'):
            save_data.player = PlayerSaveData(**data['player'])

        save_data.party = [PlayerSaveData(**p) for p in data.get('party', [])]

        if data.get('inventory'):
            save_data.inventory = InventorySaveData(**data['inventory'])

        save_data.current_map = data.get('current_map', '')
        save_data.quests = data.get('quests', {})
        save_data.flags = data.get('flags', {})
        save_data.custom_data = data.get('custom_data', {})

        return save_data

    def _apply_save_data(self, save_data: GameSaveData) -> None:
        """Apply save data to game state."""
        # Restore flags
        self._flags = save_data.flags.copy()

        # Restore playtime
        if save_data.metadata:
            self._playtime = save_data.metadata.playtime_seconds

        # Restore quests
        if self.quest_manager and save_data.quests:
            self.quest_manager.load_save_data(save_data.quests)

        # TODO: Restore player position, stats, inventory
        # This requires the game to be set up to receive this data
