"""
Interaction system - handles player interactions with objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Callable
from dataclasses import dataclass

from engine.core import System, World, Entity
from engine.core.actions import Action
from engine.core.events import EventBus, EngineEvent
from framework.components import (
    Transform,
    Collider,
    Direction,
    Interactable,
    InteractionType,
    TriggerZone,
    Chest,
    Door,
    SavePoint,
    DialogSpeaker,
)

if TYPE_CHECKING:
    from engine.input.handler import InputHandler


@dataclass
class InteractionEvent:
    """Data for an interaction event."""
    player: Entity
    target: Entity
    interaction_type: InteractionType


class InteractionSystem(System):
    """
    Handles player interactions with objects and NPCs.

    Responsibilities:
    - Detecting nearby interactables
    - Processing interaction input
    - Triggering appropriate responses
    """

    def __init__(
        self,
        world: World,
        events: EventBus,
        input_handler: InputHandler,
    ):
        super().__init__(world)
        self.events = events
        self.input = input_handler

        self._player: Optional[Entity] = None
        self._nearest_interactable: Optional[Entity] = None
        self._interaction_range = 24.0

        # Callbacks for different interaction types
        self._handlers: dict[InteractionType, Callable[[InteractionEvent], None]] = {}

    def set_player(self, player: Entity) -> None:
        """Set the player entity."""
        self._player = player

    def register_handler(
        self,
        interaction_type: InteractionType,
        handler: Callable[[InteractionEvent], None],
    ) -> None:
        """Register a handler for an interaction type."""
        self._handlers[interaction_type] = handler

    def get_nearest_interactable(self) -> Optional[Entity]:
        """Get the nearest interactable entity."""
        return self._nearest_interactable

    def update(self, dt: float) -> None:
        """Update interaction system."""
        if not self._player:
            return

        player_t = self._player.get(Transform)
        if not player_t:
            return

        # Update cooldowns
        for entity_id in self.world.get_entities_with_components(Interactable):
            entity = self.world.get_entity(entity_id)
            if entity:
                interact = entity.get(Interactable)
                if interact:
                    interact.update_cooldown(dt)

        # Find nearest interactable
        self._nearest_interactable = self._find_nearest_interactable(player_t)

        # Process trigger zones
        self._process_triggers(player_t)

        # Check for interaction input
        if self.input.is_action_pressed(Action.CONFIRM):
            if self._nearest_interactable:
                self._interact(self._nearest_interactable)

    def _find_nearest_interactable(
        self,
        player_t: Transform,
    ) -> Optional[Entity]:
        """Find the nearest interactable entity."""
        nearest: Optional[Entity] = None
        nearest_dist = float('inf')

        # Get interaction point (in front of player)
        facing_vec = player_t.facing.vector
        check_x = player_t.x + facing_vec[0] * self._interaction_range * 0.5
        check_y = player_t.y + facing_vec[1] * self._interaction_range * 0.5

        for entity_id in self.world.get_entities_with_components(
            Transform, Interactable
        ):
            entity = self.world.get_entity(entity_id)
            if not entity or entity.id == self._player.id:
                continue

            target_t = entity.get(Transform)
            interact = entity.get(Interactable)

            if not target_t or not interact:
                continue

            if not interact.can_interact():
                continue

            # Calculate distance
            dx = target_t.x - player_t.x
            dy = target_t.y - player_t.y
            dist = (dx * dx + dy * dy) ** 0.5

            if dist > interact.interaction_range:
                continue

            # Check facing requirement
            if interact.requires_facing:
                # Check if player is facing the target
                facing_check_dist = (
                    (target_t.x - check_x) ** 2 +
                    (target_t.y - check_y) ** 2
                ) ** 0.5
                if facing_check_dist > dist:
                    continue

            if dist < nearest_dist:
                nearest = entity
                nearest_dist = dist

        return nearest

    def _interact(self, target: Entity) -> None:
        """Perform interaction with target entity."""
        interact = target.get(Interactable)
        if not interact or not interact.can_interact():
            return

        # Create event
        event = InteractionEvent(
            player=self._player,
            target=target,
            interaction_type=interact.interaction_type,
        )

        # Start cooldown
        interact.start_cooldown()

        # Call registered handler
        if interact.interaction_type in self._handlers:
            self._handlers[interact.interaction_type](event)

        # Handle built-in types
        self._handle_builtin_interaction(event)

    def _handle_builtin_interaction(self, event: InteractionEvent) -> None:
        """Handle built-in interaction types."""
        target = event.target
        itype = event.interaction_type

        if itype == InteractionType.TALK:
            speaker = target.get(DialogSpeaker)
            if speaker and speaker.dialog_id:
                # Emit dialog start event
                self.events.emit(EngineEvent.SCENE_TRANSITION, {
                    'type': 'dialog_start',
                    'dialog_id': speaker.dialog_id,
                    'speaker': speaker.name,
                    'portrait': speaker.portrait_id,
                })

        elif itype == InteractionType.OPEN:
            chest = target.get(Chest)
            if chest and chest.can_open():
                items, gold = chest.open()
                self.events.emit(EngineEvent.ENTITY_REMOVED, {
                    'type': 'chest_opened',
                    'items': items,
                    'gold': gold,
                    'entity_id': target.id,
                })

        elif itype == InteractionType.ENTER:
            door = target.get(Door)
            if door and door.can_enter():
                self.events.emit(EngineEvent.SCENE_TRANSITION, {
                    'type': 'map_transition',
                    'target_map': door.target_map,
                    'target_x': door.target_x,
                    'target_y': door.target_y,
                    'transition': door.transition_type,
                })

        elif itype == InteractionType.READ:
            interact = target.get(Interactable)
            if interact:
                text = interact.data.get('text', '')
                self.events.emit(EngineEvent.SCENE_TRANSITION, {
                    'type': 'show_message',
                    'text': text,
                })

        elif itype == InteractionType.SAVE:
            save_point = target.get(SavePoint)
            if save_point and save_point.is_active:
                self.events.emit(EngineEvent.SCENE_TRANSITION, {
                    'type': 'save_prompt',
                    'heal': save_point.heal_on_save,
                })

    def _process_triggers(self, player_t: Transform) -> None:
        """Process trigger zones."""
        player_id = self._player.id if self._player else -1

        for entity_id in self.world.get_entities_with_components(
            Transform, TriggerZone
        ):
            entity = self.world.get_entity(entity_id)
            if not entity:
                continue

            trigger_t = entity.get(Transform)
            trigger = entity.get(TriggerZone)

            if not trigger_t or not trigger:
                continue

            if not trigger.can_trigger():
                continue

            # Check if player is inside trigger
            in_zone = (
                trigger_t.x <= player_t.x < trigger_t.x + trigger.width and
                trigger_t.y <= player_t.y < trigger_t.y + trigger.height
            )

            was_inside = player_id in trigger.entities_inside

            if in_zone and not was_inside:
                # Player entered
                trigger.entity_entered(player_id)
                if trigger.on_enter:
                    self.events.emit(EngineEvent.SCENE_TRANSITION, {
                        'type': 'trigger_enter',
                        'script': trigger.on_enter,
                        'entity_id': entity.id,
                    })
                if trigger.once_only:
                    trigger.mark_fired()

            elif not in_zone and was_inside:
                # Player exited
                trigger.entity_exited(player_id)
                if trigger.on_exit:
                    self.events.emit(EngineEvent.SCENE_TRANSITION, {
                        'type': 'trigger_exit',
                        'script': trigger.on_exit,
                        'entity_id': entity.id,
                    })

            elif in_zone and was_inside and trigger.on_stay:
                # Player staying
                self.events.emit(EngineEvent.SCENE_TRANSITION, {
                    'type': 'trigger_stay',
                    'script': trigger.on_stay,
                    'entity_id': entity.id,
                })
