"""
Item system - item definitions and database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum, auto
from pathlib import Path
import json

from framework.components import EquipmentSlot, ItemType


class ItemRarity(Enum):
    """Item rarity levels."""
    COMMON = auto()
    UNCOMMON = auto()
    RARE = auto()
    EPIC = auto()
    LEGENDARY = auto()


@dataclass
class ItemStats:
    """Stat modifiers from equipment."""
    strength: int = 0
    defense: int = 0
    magic: int = 0
    resistance: int = 0
    agility: int = 0
    luck: int = 0
    max_hp: int = 0
    max_mp: int = 0


@dataclass
class ItemDefinition:
    """Complete item definition."""
    id: str
    name: str
    description: str = ""
    item_type: ItemType = ItemType.CONSUMABLE
    rarity: ItemRarity = ItemRarity.COMMON

    # Stacking
    max_stack: int = 99
    is_key_item: bool = False

    # Value
    buy_price: int = 0
    sell_price: int = 0

    # Equipment
    equipment_slot: Optional[EquipmentSlot] = None
    stats: ItemStats = field(default_factory=ItemStats)

    # Consumable effects
    hp_restore: int = 0
    mp_restore: int = 0
    revive: bool = False

    # Battle use
    usable_in_battle: bool = False
    usable_in_field: bool = True
    battle_skill_id: Optional[str] = None

    # Display
    icon_id: str = ""
    sprite_id: str = ""


class ItemDatabase:
    """
    Database of all item definitions.
    """

    def __init__(self, data_path: str = "game/data/database"):
        self.data_path = Path(data_path)
        self._items: dict[str, ItemDefinition] = {}

    def load_items(self, filename: str = "items.json") -> None:
        """Load item definitions from JSON."""
        path = self.data_path / filename
        if not path.exists():
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for item_data in data.get('items', []):
            item = self._parse_item(item_data)
            self._items[item.id] = item

    def _parse_item(self, data: dict) -> ItemDefinition:
        """Parse an item from JSON data."""
        item = ItemDefinition(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            item_type=ItemType[data.get('type', 'CONSUMABLE').upper()],
            rarity=ItemRarity[data.get('rarity', 'COMMON').upper()],
            max_stack=data.get('max_stack', 99),
            is_key_item=data.get('key_item', False),
            buy_price=data.get('buy_price', 0),
            sell_price=data.get('sell_price', data.get('buy_price', 0) // 2),
            hp_restore=data.get('hp_restore', 0),
            mp_restore=data.get('mp_restore', 0),
            revive=data.get('revive', False),
            usable_in_battle=data.get('battle_use', False),
            usable_in_field=data.get('field_use', True),
            battle_skill_id=data.get('battle_skill'),
            icon_id=data.get('icon', ''),
            sprite_id=data.get('sprite', ''),
        )

        # Equipment
        if 'slot' in data:
            item.equipment_slot = EquipmentSlot[data['slot'].upper()]
            item.item_type = ItemType.EQUIPMENT
            item.max_stack = 1

        # Stats
        if 'stats' in data:
            stats_data = data['stats']
            item.stats = ItemStats(
                strength=stats_data.get('str', 0),
                defense=stats_data.get('def', 0),
                magic=stats_data.get('mag', 0),
                resistance=stats_data.get('res', 0),
                agility=stats_data.get('agi', 0),
                luck=stats_data.get('luk', 0),
                max_hp=stats_data.get('hp', 0),
                max_mp=stats_data.get('mp', 0),
            )

        return item

    def get_item(self, item_id: str) -> Optional[ItemDefinition]:
        """Get an item definition."""
        return self._items.get(item_id)

    def get_items_by_type(self, item_type: ItemType) -> list[ItemDefinition]:
        """Get all items of a type."""
        return [i for i in self._items.values() if i.item_type == item_type]

    def get_equipment_for_slot(self, slot: EquipmentSlot) -> list[ItemDefinition]:
        """Get all equipment for a slot."""
        return [i for i in self._items.values() if i.equipment_slot == slot]

    def register_item(self, item: ItemDefinition) -> None:
        """Register an item definition."""
        self._items[item.id] = item
