"""
Interaction components - interactable objects, triggers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Any

from engine.core.component import Component


class InteractionType(Enum):
    """Types of interactions."""
    NONE = auto()
    TALK = auto()       # Talk to NPC
    EXAMINE = auto()    # Examine object
    OPEN = auto()       # Open chest/door
    PICKUP = auto()     # Pick up item
    USE = auto()        # Use mechanism
    ENTER = auto()      # Enter door/portal
    READ = auto()       # Read sign/book
    SAVE = auto()       # Save point


@dataclass
class Interactable(Component):
    """
    Makes an entity interactable.

    Attributes:
        interaction_type: Type of interaction
        prompt_text: Text shown when near ("Press E to talk")
        is_enabled: Whether interaction is currently possible
        requires_facing: Must player face this to interact
        interaction_range: Range to trigger prompt
        cooldown: Time between interactions
        cooldown_timer: Current cooldown
        on_interact: Script to run on interaction
        on_complete: Script to run when interaction ends
        data: Custom data for the interaction
    """
    interaction_type: InteractionType = InteractionType.EXAMINE
    prompt_text: str = "Interact"
    is_enabled: bool = True
    requires_facing: bool = True
    interaction_range: float = 24.0
    cooldown: float = 0.0
    cooldown_timer: float = 0.0
    on_interact: Optional[str] = None
    on_complete: Optional[str] = None
    data: dict[str, Any] = field(default_factory=dict)

    def can_interact(self) -> bool:
        """Check if interaction is currently possible."""
        return self.is_enabled and self.cooldown_timer <= 0

    def start_cooldown(self) -> None:
        """Start the cooldown timer."""
        self.cooldown_timer = self.cooldown

    def update_cooldown(self, dt: float) -> None:
        """Update cooldown timer."""
        if self.cooldown_timer > 0:
            self.cooldown_timer = max(0, self.cooldown_timer - dt)


@dataclass
class TriggerZone(Component):
    """
    Invisible trigger zone.

    Attributes:
        width: Zone width
        height: Zone height
        is_active: Whether trigger is active
        once_only: Trigger only fires once
        has_fired: Whether once-only trigger has fired
        on_enter: Script when entity enters
        on_exit: Script when entity exits
        on_stay: Script while entity is inside
        filter_tags: Only trigger for entities with these tags
        entities_inside: Set of entity IDs currently inside
    """
    width: float = 32.0
    height: float = 32.0
    is_active: bool = True
    once_only: bool = False
    has_fired: bool = False
    on_enter: Optional[str] = None
    on_exit: Optional[str] = None
    on_stay: Optional[str] = None
    filter_tags: set[str] = field(default_factory=set)
    entities_inside: set[int] = field(default_factory=set)

    def can_trigger(self) -> bool:
        """Check if trigger can fire."""
        if not self.is_active:
            return False
        if self.once_only and self.has_fired:
            return False
        return True

    def entity_entered(self, entity_id: int) -> bool:
        """
        Called when entity enters zone.

        Returns:
            True if this is a new entry
        """
        if entity_id not in self.entities_inside:
            self.entities_inside.add(entity_id)
            return True
        return False

    def entity_exited(self, entity_id: int) -> bool:
        """
        Called when entity exits zone.

        Returns:
            True if entity was inside
        """
        if entity_id in self.entities_inside:
            self.entities_inside.discard(entity_id)
            return True
        return False

    def mark_fired(self) -> None:
        """Mark once-only trigger as fired."""
        self.has_fired = True


@dataclass
class Chest(Component):
    """
    Chest/container with loot.

    Attributes:
        is_open: Whether chest has been opened
        is_locked: Whether chest is locked
        key_item_id: Item ID required to unlock (if locked)
        contents: List of (item_id, quantity) tuples
        gold: Gold amount in chest
        on_open: Script to run when opened
    """
    is_open: bool = False
    is_locked: bool = False
    key_item_id: Optional[str] = None
    contents: list[tuple[str, int]] = field(default_factory=list)
    gold: int = 0
    on_open: Optional[str] = None

    def can_open(self, has_key: bool = False) -> bool:
        """Check if chest can be opened."""
        if self.is_open:
            return False
        if self.is_locked and not has_key:
            return False
        return True

    def open(self) -> tuple[list[tuple[str, int]], int]:
        """
        Open the chest.

        Returns:
            (contents, gold)
        """
        if not self.is_open:
            self.is_open = True
            items = self.contents.copy()
            gold = self.gold
            self.contents.clear()
            self.gold = 0
            return items, gold
        return [], 0


@dataclass
class Door(Component):
    """
    Door/portal for map transitions.

    Attributes:
        target_map: Map ID to transition to
        target_x: Spawn X position in target map
        target_y: Spawn Y position in target map
        target_facing: Player facing after transition
        is_locked: Whether door is locked
        key_item_id: Item ID required to unlock
        transition_type: Type of screen transition
        on_enter: Script to run before transition
    """
    target_map: str = ""
    target_x: float = 0.0
    target_y: float = 0.0
    target_facing: str = "down"
    is_locked: bool = False
    key_item_id: Optional[str] = None
    transition_type: str = "fade"
    on_enter: Optional[str] = None

    def can_enter(self, has_key: bool = False) -> bool:
        """Check if door can be entered."""
        if self.is_locked and not has_key:
            return False
        return bool(self.target_map)


@dataclass
class SavePoint(Component):
    """
    Save point marker.

    Attributes:
        is_active: Whether save point is usable
        heal_on_save: Whether to heal party on save
        prompt_text: Text to show
    """
    is_active: bool = True
    heal_on_save: bool = True
    prompt_text: str = "Save your progress?"
