"""
Inventory components - items, equipment, container.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Optional, Callable, Iterator

from pydantic import Field
from dataclasses import dataclass

from engine.core.component import Component


class EquipmentSlot(Enum):
    """Equipment slot types."""
    NONE = auto()
    WEAPON = auto()
    SHIELD = auto()
    HEAD = auto()
    BODY = auto()
    HANDS = auto()
    FEET = auto()
    ACCESSORY_1 = auto()
    ACCESSORY_2 = auto()


class ItemType(Enum):
    """Item categories."""
    CONSUMABLE = auto()    # Potions, food
    EQUIPMENT = auto()     # Weapons, armor
    KEY_ITEM = auto()      # Quest items
    MATERIAL = auto()      # Crafting materials
    CURRENCY = auto()      # Gold, special currencies


@dataclass
class ItemStack:
    """
    A stack of items in inventory.

    Attributes:
        item_id: Reference to item definition
        quantity: Number of items in stack
        max_stack: Maximum stack size
    """
    item_id: str = ""
    quantity: int = 1
    max_stack: int = 99

    @property
    def is_full(self) -> bool:
        """Check if stack is at max."""
        return self.quantity >= self.max_stack

    @property
    def is_empty(self) -> bool:
        """Check if stack is empty."""
        return self.quantity <= 0

    def add(self, amount: int = 1) -> int:
        """
        Add to stack.

        Returns:
            Amount that couldn't be added (overflow)
        """
        space = self.max_stack - self.quantity
        to_add = min(amount, space)
        self.quantity += to_add
        return amount - to_add

    def remove(self, amount: int = 1) -> int:
        """
        Remove from stack.

        Returns:
            Actual amount removed
        """
        to_remove = min(amount, self.quantity)
        self.quantity -= to_remove
        return to_remove

    def can_stack_with(self, other: ItemStack) -> bool:
        """Check if can stack with another item."""
        return (
            self.item_id == other.item_id and
            not self.is_full
        )


class Inventory(Component):
    """
    Item container.

    Attributes:
        slots: List of item stacks (None = empty slot)
        max_slots: Maximum inventory size
        gold: Currency amount
    """
    slots: list[Optional[ItemStack]] = Field(default_factory=list)
    max_slots: int = 20
    gold: int = 0

    def model_post_init(self, __context):
        """Initialize empty slots."""
        if not self.slots:
            self.slots = [None] * self.max_slots
        # Ensure we have enough slots
        while len(self.slots) < self.max_slots:
            self.slots.append(None)

    @property
    def free_slots(self) -> int:
        """Count empty slots."""
        return sum(1 for s in self.slots if s is None)

    @property
    def is_full(self) -> bool:
        """Check if inventory is full."""
        return self.free_slots == 0

    def add_item(self, item_id: str, quantity: int = 1, max_stack: int = 99) -> int:
        """
        Add item to inventory.

        Args:
            item_id: Item definition ID
            quantity: Amount to add
            max_stack: Maximum stack size for this item

        Returns:
            Amount that couldn't be added
        """
        remaining = quantity

        # First, try to stack with existing items
        for slot in self.slots:
            if slot and slot.item_id == item_id and not slot.is_full:
                remaining = slot.add(remaining)
                if remaining <= 0:
                    return 0

        # Then, add to empty slots
        for i, slot in enumerate(self.slots):
            if slot is None:
                new_stack = ItemStack(item_id=item_id, quantity=0, max_stack=max_stack)
                remaining = new_stack.add(remaining)
                self.slots[i] = new_stack
                if remaining <= 0:
                    return 0

        return remaining

    def remove_item(self, item_id: str, quantity: int = 1) -> int:
        """
        Remove item from inventory.

        Args:
            item_id: Item definition ID
            quantity: Amount to remove

        Returns:
            Amount actually removed
        """
        remaining = quantity
        removed = 0

        for i, slot in enumerate(self.slots):
            if slot and slot.item_id == item_id:
                taken = slot.remove(remaining)
                removed += taken
                remaining -= taken

                # Clear empty slots
                if slot.is_empty:
                    self.slots[i] = None

                if remaining <= 0:
                    break

        return removed

    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        """Check if inventory contains enough of an item."""
        return self.count_item(item_id) >= quantity

    def count_item(self, item_id: str) -> int:
        """Count total quantity of an item."""
        return sum(
            s.quantity for s in self.slots
            if s and s.item_id == item_id
        )

    def get_slot(self, index: int) -> Optional[ItemStack]:
        """Get item at slot index."""
        if 0 <= index < len(self.slots):
            return self.slots[index]
        return None

    def swap_slots(self, index_a: int, index_b: int) -> bool:
        """Swap two inventory slots."""
        if 0 <= index_a < len(self.slots) and 0 <= index_b < len(self.slots):
            self.slots[index_a], self.slots[index_b] = (
                self.slots[index_b], self.slots[index_a]
            )
            return True
        return False

    def add_gold(self, amount: int) -> None:
        """Add gold."""
        self.gold = max(0, self.gold + amount)

    def spend_gold(self, amount: int) -> bool:
        """Spend gold if available."""
        if self.gold >= amount:
            self.gold -= amount
            return True
        return False

    # Filtering methods

    def get_items(self) -> list[ItemStack]:
        """
        Get all non-empty item stacks.

        Returns:
            List of ItemStack objects (no None values)
        """
        return [slot for slot in self.slots if slot is not None]

    def get_item_ids(self) -> list[str]:
        """
        Get unique item IDs in inventory.

        Returns:
            List of unique item ID strings
        """
        return list({slot.item_id for slot in self.slots if slot is not None})

    def iter_items(self) -> Iterator[tuple[int, ItemStack]]:
        """
        Iterate over items with their slot indices.

        Yields:
            (slot_index, ItemStack) tuples for non-empty slots
        """
        for i, slot in enumerate(self.slots):
            if slot is not None:
                yield i, slot

    def filter_items(
        self,
        predicate: Callable[[str], bool],
    ) -> list[ItemStack]:
        """
        Filter items by a predicate function.

        The predicate receives the item_id and returns True to include.

        Args:
            predicate: Function(item_id) -> bool

        Returns:
            List of matching ItemStacks

        Example:
            # Get all potions (assuming item_database lookup)
            potions = inventory.filter_items(
                lambda id: item_database[id].type == ItemType.CONSUMABLE
            )
        """
        return [
            slot for slot in self.slots
            if slot is not None and predicate(slot.item_id)
        ]

    def filter_item_ids(
        self,
        predicate: Callable[[str], bool],
    ) -> list[str]:
        """
        Filter and return matching item IDs.

        Args:
            predicate: Function(item_id) -> bool

        Returns:
            List of matching item IDs (unique)
        """
        return list({
            slot.item_id for slot in self.slots
            if slot is not None and predicate(slot.item_id)
        })

    def get_stacks_of(self, item_id: str) -> list[ItemStack]:
        """
        Get all stacks of a specific item.

        Args:
            item_id: Item ID to find

        Returns:
            List of ItemStacks with matching item_id
        """
        return [
            slot for slot in self.slots
            if slot is not None and slot.item_id == item_id
        ]


class Equipment(Component):
    """
    Equipped items on a character.

    Attributes:
        slots: Map of slot type to equipped item ID
    """
    slots: dict[EquipmentSlot, Optional[str]] = Field(default_factory=dict)

    def model_post_init(self, __context):
        """Initialize all equipment slots."""
        for slot in EquipmentSlot:
            if slot not in self.slots and slot != EquipmentSlot.NONE:
                self.slots[slot] = None

    def equip(self, slot: EquipmentSlot, item_id: str) -> Optional[str]:
        """
        Equip an item.

        Args:
            slot: Equipment slot
            item_id: Item to equip

        Returns:
            Previously equipped item ID (or None)
        """
        previous = self.slots.get(slot)
        self.slots[slot] = item_id
        return previous

    def unequip(self, slot: EquipmentSlot) -> Optional[str]:
        """
        Unequip from a slot.

        Returns:
            Unequipped item ID (or None)
        """
        previous = self.slots.get(slot)
        self.slots[slot] = None
        return previous

    def get_equipped(self, slot: EquipmentSlot) -> Optional[str]:
        """Get item ID in a slot."""
        return self.slots.get(slot)

    def is_equipped(self, item_id: str) -> bool:
        """Check if an item is equipped anywhere."""
        return item_id in self.slots.values()

    def get_all_equipped(self) -> list[str]:
        """Get list of all equipped item IDs."""
        return [item_id for item_id in self.slots.values() if item_id]
