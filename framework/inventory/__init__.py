"""
Inventory module - items and equipment.

Provides:
- Item definitions and database
- Item stats and effects
"""

from framework.inventory.items import (
    ItemDatabase,
    ItemDefinition,
    ItemStats,
    ItemRarity,
)

__all__ = [
    "ItemDatabase",
    "ItemDefinition",
    "ItemStats",
    "ItemRarity",
]
