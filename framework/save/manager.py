"""
Save/Load system - game state persistence.

Provides:
- Save/load game state to JSON files
- Multiple save slots (10 by default)
- Auto-save functionality
- Save integrity validation (checksum)
- Game flags for progression tracking
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional, Any, Callable
from pathlib import Path
from datetime import datetime
import json
import hashlib
import base64

from engine.core import World, Entity
from engine.core.events import EventBus
from framework.components import (
    Transform,
    Velocity,
    Health,
    Mana,
    CharacterStats,
    Experience,
    Inventory,
    Equipment,
)
from framework.components.inventory import ItemStack, EquipmentSlot

if TYPE_CHECKING:
    from framework.world.map import MapManager
    from framework.progression.quests import QuestManager


class SaveEvent(Enum):
    """Save system events."""
    SAVE_STARTED = auto()
    SAVE_COMPLETED = auto()
    SAVE_FAILED = auto()
    LOAD_STARTED = auto()
    LOAD_COMPLETED = auto()
    LOAD_FAILED = auto()
    AUTO_SAVE_TRIGGERED = auto()


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

    Features:
    - 10 save slots (configurable)
    - Auto-save with configurable triggers
    - Checksum validation for save integrity
    - Event publishing for save/load operations
    - Game flags for story progression

    Usage:
        save_mgr = SaveManager(world=world, event_bus=event_bus)
        save_mgr.save_game(slot=0, name="My Save")
        save_mgr.load_game(slot=0)

        # Auto-save
        save_mgr.enable_auto_save(interval=300)  # Every 5 minutes
    """

    VERSION = "1.0"
    MAX_SLOTS = 10
    AUTO_SAVE_SLOT = 99  # Special slot for auto-saves

    def __init__(
        self,
        save_path: str = "game/saves",
        world: Optional[World] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.save_path = Path(save_path)
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.world = world
        self.event_bus = event_bus

        # External managers (set by game)
        self.quest_manager: Optional[QuestManager] = None
        self.map_manager: Optional[MapManager] = None

        # Runtime tracking
        self._playtime: int = 0  # Seconds
        self._current_slot: Optional[int] = None

        # Game flags (for story progression, switches, etc.)
        self._flags: dict[str, Any] = {}

        # Auto-save settings
        self._auto_save_enabled: bool = False
        self._auto_save_interval: float = 300.0  # 5 minutes
        self._auto_save_timer: float = 0.0
        self._auto_save_on_map_change: bool = True

        # Callbacks for custom entity restoration
        self._on_player_restored: Optional[Callable[[Entity, PlayerSaveData], None]] = None
        self._on_load_complete: Optional[Callable[[GameSaveData], None]] = None

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

        # Publish start event
        if self.event_bus:
            self.event_bus.publish(SaveEvent.SAVE_STARTED, slot=slot)

        try:
            # Create save data
            save_data = self._create_save_data(slot, name)
            if custom_data:
                save_data.custom_data = custom_data

            # Serialize
            save_dict = self._serialize_save_data(save_data)

            # Add checksum
            save_dict['checksum'] = self._calculate_checksum(save_dict)

            # Write save file
            save_path = self._get_slot_path(slot)
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(save_dict, f, indent=2)

            # Write metadata
            meta_path = self._get_metadata_path(slot)
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(save_data.metadata), f, indent=2)

            self._current_slot = slot

            # Publish success event
            if self.event_bus:
                self.event_bus.publish(SaveEvent.SAVE_COMPLETED, slot=slot)

            return True

        except Exception as e:
            print(f"Save failed: {e}")
            # Publish failure event
            if self.event_bus:
                self.event_bus.publish(SaveEvent.SAVE_FAILED, slot=slot, error=str(e))
            return False

    def load_game(self, slot: int, validate: bool = True) -> bool:
        """
        Load a saved game.

        Args:
            slot: Save slot number
            validate: Whether to validate checksum

        Returns:
            True if load was successful
        """
        save_path = self._get_slot_path(slot)
        if not save_path.exists():
            return False

        # Publish start event
        if self.event_bus:
            self.event_bus.publish(SaveEvent.LOAD_STARTED, slot=slot)

        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                save_dict = json.load(f)

            # Validate checksum if present and validation enabled
            if validate:
                checksum = save_dict.get('checksum')
                if checksum and not self._verify_checksum(save_dict, checksum):
                    print(f"Save file corrupted: checksum mismatch")
                    if self.event_bus:
                        self.event_bus.publish(
                            SaveEvent.LOAD_FAILED,
                            slot=slot,
                            error="Checksum validation failed",
                        )
                    return False

            save_data = self._deserialize_save_data(save_dict)
            self._apply_save_data(save_data)

            self._current_slot = slot

            # Publish success event
            if self.event_bus:
                self.event_bus.publish(SaveEvent.LOAD_COMPLETED, slot=slot)

            return True

        except Exception as e:
            print(f"Load failed: {e}")
            # Publish failure event
            if self.event_bus:
                self.event_bus.publish(SaveEvent.LOAD_FAILED, slot=slot, error=str(e))
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
        if not self.world:
            return

        # Restore flags
        self._flags = save_data.flags.copy()

        # Restore playtime
        if save_data.metadata:
            self._playtime = save_data.metadata.playtime_seconds

        # Restore quests
        if self.quest_manager and save_data.quests:
            self.quest_manager.load_save_data(save_data.quests)

        # Restore player
        if save_data.player:
            player = self._find_entity_by_tag("player")
            if player:
                self._restore_entity(player, save_data.player)

        # Restore party members
        party_members = list(self._find_entities_by_tag("party_member"))
        for i, party_data in enumerate(save_data.party):
            if i < len(party_members):
                self._restore_entity(party_members[i], party_data)

        # Restore inventory
        if save_data.inventory:
            player = self._find_entity_by_tag("player")
            if player:
                self._restore_inventory(player, save_data.inventory)

        # Load map (if map manager available)
        if self.map_manager and save_data.current_map:
            self.map_manager.load_map(save_data.current_map)

        # Call completion callback
        if self._on_load_complete:
            self._on_load_complete(save_data)

    def _find_entity_by_tag(self, tag: str) -> Optional[Entity]:
        """Find first entity with a tag."""
        if not self.world:
            return None
        for entity in self.world.entities:
            if tag in entity.tags:
                return entity
        return None

    def _find_entities_by_tag(self, tag: str):
        """Find all entities with a tag."""
        if not self.world:
            return
        for entity in self.world.entities:
            if tag in entity.tags:
                yield entity

    def _restore_entity(self, entity: Entity, data: PlayerSaveData) -> None:
        """Restore entity components from save data."""
        # Transform
        transform = entity.try_get(Transform)
        if transform:
            transform.x = data.x
            transform.y = data.y
            # Restore facing direction
            from framework.components.transform import Direction
            try:
                transform.facing = Direction[data.facing]
            except KeyError:
                pass

        # Health
        health = entity.try_get(Health)
        if health:
            health.current = data.hp
            health.max_hp = data.max_hp
            health.is_dead = data.hp <= 0

        # Mana
        mana = entity.try_get(Mana)
        if mana:
            mana.current = data.mp
            mana.max_mp = data.max_mp

        # Stats
        stats = entity.try_get(CharacterStats)
        if stats and data.stats:
            stats.strength = data.stats.get('strength', stats.strength)
            stats.defense = data.stats.get('defense', stats.defense)
            stats.magic = data.stats.get('magic', stats.magic)
            stats.resistance = data.stats.get('resistance', stats.resistance)
            stats.agility = data.stats.get('agility', stats.agility)
            stats.luck = data.stats.get('luck', stats.luck)
            stats.level = data.level

        # Experience
        exp = entity.try_get(Experience)
        if exp:
            exp.current = data.exp
            exp.total = data.exp_total
            exp.level = data.level

        # Equipment
        equipment = entity.try_get(Equipment)
        if equipment and data.equipment:
            for slot_name, item_id in data.equipment.items():
                try:
                    slot = EquipmentSlot[slot_name]
                    equipment.slots[slot] = item_id
                except KeyError:
                    pass

        # Custom callback
        if self._on_player_restored:
            self._on_player_restored(entity, data)

    def _restore_inventory(self, entity: Entity, data: InventorySaveData) -> None:
        """Restore inventory from save data."""
        inv = entity.try_get(Inventory)
        if not inv:
            return

        inv.gold = data.gold

        # Clear existing slots
        inv.slots = [None] * inv.max_slots

        # Restore items
        for item_data in data.items:
            item_id = item_data.get('item_id', '')
            quantity = item_data.get('quantity', 1)
            if item_id:
                inv.add_item(item_id, quantity)

    # Auto-save

    def enable_auto_save(
        self,
        interval: float = 300.0,
        on_map_change: bool = True,
    ) -> None:
        """
        Enable auto-save functionality.

        Args:
            interval: Seconds between auto-saves (0 to disable timed saves)
            on_map_change: Whether to auto-save on map transitions
        """
        self._auto_save_enabled = True
        self._auto_save_interval = interval
        self._auto_save_on_map_change = on_map_change
        self._auto_save_timer = 0.0

    def disable_auto_save(self) -> None:
        """Disable auto-save."""
        self._auto_save_enabled = False

    def update(self, dt: float) -> None:
        """
        Update save manager (call each frame).

        Handles playtime tracking and auto-save timer.
        """
        self._playtime += int(dt)

        if self._auto_save_enabled and self._auto_save_interval > 0:
            self._auto_save_timer += dt
            if self._auto_save_timer >= self._auto_save_interval:
                self._auto_save_timer = 0.0
                self.auto_save()

    def auto_save(self) -> bool:
        """Perform an auto-save."""
        if self.event_bus:
            self.event_bus.publish(SaveEvent.AUTO_SAVE_TRIGGERED)

        return self.save_game(
            slot=self.AUTO_SAVE_SLOT,
            name="Auto Save",
        )

    def trigger_map_change_save(self) -> None:
        """Called when map changes to trigger auto-save if enabled."""
        if self._auto_save_enabled and self._auto_save_on_map_change:
            self.auto_save()

    # Checksum validation

    def _calculate_checksum(self, data: dict) -> str:
        """Calculate checksum for save data."""
        # Create a deterministic JSON string
        json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        # Calculate SHA-256 hash
        hash_bytes = hashlib.sha256(json_str.encode('utf-8')).digest()
        # Return base64 encoded hash
        return base64.b64encode(hash_bytes).decode('ascii')

    def _verify_checksum(self, data: dict, expected_checksum: str) -> bool:
        """Verify save data checksum."""
        # Remove checksum from data for verification
        data_copy = data.copy()
        data_copy.pop('checksum', None)
        actual_checksum = self._calculate_checksum(data_copy)
        return actual_checksum == expected_checksum

    def validate_save(self, slot: int) -> bool:
        """
        Validate a save file's integrity.

        Returns:
            True if save is valid, False if corrupted or missing
        """
        save_path = self._get_slot_path(slot)
        if not save_path.exists():
            return False

        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            checksum = data.get('checksum')
            if not checksum:
                # No checksum = old save format, assume valid
                return True

            return self._verify_checksum(data, checksum)
        except (json.JSONDecodeError, IOError):
            return False

    # Callbacks

    def on_player_restored(self, callback: Callable[[Entity, PlayerSaveData], None]) -> None:
        """Set callback for when player entity is restored."""
        self._on_player_restored = callback

    def on_load_complete(self, callback: Callable[[GameSaveData], None]) -> None:
        """Set callback for when load is complete."""
        self._on_load_complete = callback

    # Properties

    @property
    def playtime(self) -> int:
        """Get total playtime in seconds."""
        return self._playtime

    @property
    def playtime_formatted(self) -> str:
        """Get playtime as HH:MM:SS string."""
        hours = self._playtime // 3600
        minutes = (self._playtime % 3600) // 60
        seconds = self._playtime % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @property
    def current_slot(self) -> Optional[int]:
        """Get the current save slot."""
        return self._current_slot

    @property
    def has_auto_save(self) -> bool:
        """Check if auto-save exists."""
        return self._get_slot_path(self.AUTO_SAVE_SLOT).exists()
