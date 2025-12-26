"""
Dialog system - manages conversation flow and UI.

Connects DialogContext components to UI widgets (DialogBox, ChoiceMenu),
handles input, loads dialog scripts from JSON, and publishes events.
"""

from __future__ import annotations

import json
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Any, Callable

from engine.core.system import System
from engine.core.events import EventBus, UIEvent, AudioEvent
from engine.core.actions import Action
from engine.ui.presets.dialog_box import DialogBox
from engine.ui.presets.choice_menu import ChoiceMenu
from framework.components.dialog import (
    DialogContext,
    DialogState,
    DialogNode,
    DialogChoice,
    DialogSpeaker,
)

if TYPE_CHECKING:
    from engine.core.entity import Entity
    from engine.core.world import World
    from engine.input.handler import InputHandler
    from engine.ui.manager import UIManager


class DialogEvent(Enum):
    """Dialog-specific events."""
    NODE_ENTERED = auto()      # Entered a new dialog node
    NODE_EXITED = auto()       # Left a dialog node
    CHOICE_SELECTED = auto()   # Player selected a choice
    TEXT_ADVANCED = auto()     # Text advanced to next character
    TEXT_COMPLETED = auto()    # All text displayed


class DialogSystem(System):
    """
    Manages dialog flow between entities and UI.

    Responsibilities:
    - Load dialog scripts from JSON
    - Update DialogContext typewriter effect
    - Sync DialogContext state to DialogBox/ChoiceMenu widgets
    - Handle input for advancing/skipping dialog
    - Publish DIALOG_STARTED/DIALOG_ENDED events
    - Trigger audio cues for text display

    Usage:
        dialog_system = DialogSystem(world, event_bus, input_handler, ui_manager)
        dialog_system.load_dialogs("game/data/database/dialog/")

        # Start a dialog
        dialog_system.start_dialog(player_entity, "dialog_intro")
    """

    required_components = [DialogContext]

    def __init__(
        self,
        world: World,
        event_bus: EventBus,
        input_handler: InputHandler,
        ui_manager: Optional[UIManager] = None,
        dialog_path: str = "game/data/database/dialog/",
    ):
        super().__init__()
        self._world = world
        self.event_bus = event_bus
        self.input_handler = input_handler
        self.ui_manager = ui_manager

        # Dialog data storage: dialog_id -> {node_id -> DialogNode}
        self._dialogs: dict[str, dict[str, DialogNode]] = {}

        # Currently active dialog entity
        self._active_entity: Optional[Entity] = None

        # UI widgets
        self._dialog_box: Optional[DialogBox] = None
        self._choice_menu: Optional[ChoiceMenu] = None

        # Audio settings
        self.text_blip_sound: Optional[str] = None
        self.text_blip_interval: int = 2  # Play blip every N characters
        self._blip_counter: int = 0

        # Event handlers for dialog scripts
        self._event_handlers: dict[str, Callable[[dict[str, Any]], None]] = {}

        # Load dialogs from default path
        self.load_dialogs(dialog_path)

    def load_dialogs(self, path: str) -> int:
        """
        Load all dialog scripts from a directory.

        Args:
            path: Directory containing dialog JSON files

        Returns:
            Number of dialogs loaded
        """
        dialog_dir = Path(path)
        if not dialog_dir.exists():
            return 0

        count = 0
        for json_file in dialog_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Handle array of dialogs or single dialog
                if isinstance(data, list):
                    for dialog_data in data:
                        self._load_dialog(dialog_data)
                        count += 1
                else:
                    self._load_dialog(data)
                    count += 1
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading dialog {json_file}: {e}")

        return count

    def _load_dialog(self, data: dict[str, Any]) -> None:
        """Load a single dialog from parsed JSON data."""
        dialog_id = data["id"]
        nodes: dict[str, DialogNode] = {}

        for node_data in data.get("nodes", []):
            node = DialogNode(
                id=node_data["id"],
                speaker=node_data.get("speaker", ""),
                text=node_data.get("text", ""),
                portrait=node_data.get("portrait"),
                next_node=node_data.get("next_node"),
                on_enter=node_data.get("on_enter"),
                on_exit=node_data.get("on_exit"),
            )

            # Parse choices
            for choice_data in node_data.get("choices", []):
                choice = DialogChoice(
                    text=choice_data["text"],
                    next_node=choice_data.get("next_node", ""),
                    condition=choice_data.get("condition"),
                    action=choice_data.get("action"),
                    disabled_text=choice_data.get("disabled_text"),
                )
                node.choices.append(choice)

            # Store events in on_enter for now (will be processed when entering node)
            if "events" in node_data:
                node.on_enter = json.dumps(node_data["events"])

            nodes[node.id] = node

        self._dialogs[dialog_id] = nodes

    def get_dialog(self, dialog_id: str) -> Optional[dict[str, DialogNode]]:
        """Get a loaded dialog by ID."""
        return self._dialogs.get(dialog_id)

    def register_event_handler(
        self,
        event_type: str,
        handler: Callable[[dict[str, Any]], None],
    ) -> None:
        """
        Register a handler for dialog script events.

        Args:
            event_type: Event type string (e.g., "give_item", "start_quest")
            handler: Callback receiving event params dict
        """
        self._event_handlers[event_type] = handler

    # Dialog flow

    def start_dialog(
        self,
        entity: Entity,
        dialog_id: str,
        start_node: str = "start",
    ) -> bool:
        """
        Start a dialog for an entity.

        Args:
            entity: Entity with DialogContext component
            dialog_id: ID of dialog script to run
            start_node: Starting node ID

        Returns:
            True if dialog started successfully
        """
        context = entity.try_get(DialogContext)
        if not context:
            return False

        dialog = self._dialogs.get(dialog_id)
        if not dialog:
            print(f"Dialog not found: {dialog_id}")
            return False

        if start_node not in dialog:
            print(f"Start node not found: {start_node} in {dialog_id}")
            return False

        # Initialize context
        context.start_dialog(dialog_id, start_node)
        self._active_entity = entity

        # Enter first node
        self._enter_node(context, dialog[start_node])

        # Create UI
        self._create_dialog_box()

        # Publish event
        self.event_bus.publish(
            UIEvent.DIALOG_STARTED,
            entity=entity,
            dialog_id=dialog_id,
        )

        return True

    def _enter_node(self, context: DialogContext, node: DialogNode) -> None:
        """Enter a dialog node."""
        context.set_node(node)
        self._blip_counter = 0

        # Process on_enter events
        if node.on_enter:
            self._process_node_events(node.on_enter)

        # Publish event
        self.event_bus.publish(
            DialogEvent.NODE_ENTERED,
            node_id=node.id,
            speaker=node.speaker,
        )

        # Update UI
        self._update_dialog_box(context)

    def _process_node_events(self, events_json: str) -> None:
        """Process events defined on a node."""
        try:
            events = json.loads(events_json)
            for event in events:
                event_type = event.get("type")
                params = event.get("params", {})

                if event_type in self._event_handlers:
                    self._event_handlers[event_type](params)
        except json.JSONDecodeError:
            # Not JSON, might be a script expression
            pass

    def advance_dialog(self) -> bool:
        """
        Advance the current dialog.

        Returns:
            True if dialog continues, False if ended
        """
        if not self._active_entity:
            return False

        context = self._active_entity.try_get(DialogContext)
        if not context or not context.is_active:
            return False

        if context.state == DialogState.DISPLAYING:
            # Skip typewriter
            context.skip_typewriter()
            self._update_dialog_box(context)
            return True

        elif context.state == DialogState.WAITING_INPUT:
            # Go to next node
            return self._go_to_next_node(context)

        elif context.state == DialogState.CHOICE_OPEN:
            # Select current choice
            return self._select_choice(context)

        return False

    def _go_to_next_node(self, context: DialogContext) -> bool:
        """Move to the next dialog node."""
        dialog = self._dialogs.get(context.current_dialog_id or "")
        if not dialog:
            self._end_dialog(context)
            return False

        current_node = dialog.get(context.current_node_id or "")
        if not current_node:
            self._end_dialog(context)
            return False

        # Process on_exit
        if current_node.on_exit:
            self._process_node_events(current_node.on_exit)

        # Publish exit event
        self.event_bus.publish(
            DialogEvent.NODE_EXITED,
            node_id=current_node.id,
        )

        # Get next node
        next_node_id = current_node.next_node
        if not next_node_id:
            self._end_dialog(context)
            return False

        next_node = dialog.get(next_node_id)
        if not next_node:
            self._end_dialog(context)
            return False

        self._enter_node(context, next_node)
        return True

    def _select_choice(self, context: DialogContext) -> bool:
        """Select the current choice and navigate to its target."""
        choice = context.get_selected_choice()
        if not choice:
            return False

        # Check condition
        if choice.condition:
            try:
                if not eval(choice.condition, {"context": context}):
                    return False
            except Exception:
                pass

        # Execute action
        if choice.action:
            try:
                exec(choice.action, {"context": context})
            except Exception:
                pass

        # Publish event
        self.event_bus.publish(
            DialogEvent.CHOICE_SELECTED,
            choice_index=context.selected_choice,
            choice_text=choice.text,
        )

        # Hide choice menu
        self._hide_choice_menu()

        # Navigate to next node
        dialog = self._dialogs.get(context.current_dialog_id or "")
        if not dialog or not choice.next_node:
            self._end_dialog(context)
            return False

        next_node = dialog.get(choice.next_node)
        if not next_node:
            self._end_dialog(context)
            return False

        self._enter_node(context, next_node)
        return True

    def _end_dialog(self, context: DialogContext) -> None:
        """End the current dialog."""
        entity = self._active_entity

        context.end_dialog()
        context.state = DialogState.INACTIVE
        self._active_entity = None

        # Remove UI
        self._destroy_dialog_box()

        # Publish event
        self.event_bus.publish(
            UIEvent.DIALOG_ENDED,
            entity=entity,
        )

    # Input handling

    def handle_input(self) -> bool:
        """
        Handle dialog input.

        Returns:
            True if input was consumed
        """
        if not self._active_entity:
            return False

        context = self._active_entity.try_get(DialogContext)
        if not context or not context.is_active:
            return False

        # Confirm advances dialog
        if self.input_handler.is_action_just_pressed(Action.CONFIRM):
            self.advance_dialog()
            return True

        # Cancel skips typewriter or advances
        if self.input_handler.is_action_just_pressed(Action.CANCEL):
            if context.state == DialogState.DISPLAYING:
                context.skip_typewriter()
                self._update_dialog_box(context)
            elif context.state == DialogState.WAITING_INPUT:
                self.advance_dialog()
            return True

        # Choice navigation
        if context.state == DialogState.CHOICE_OPEN:
            dy, _ = self.input_handler.get_menu_direction()
            if dy < 0:
                context.select_prev_choice()
                self._update_choice_menu(context)
                return True
            elif dy > 0:
                context.select_next_choice()
                self._update_choice_menu(context)
                return True

        return False

    # UI management

    def _create_dialog_box(self) -> None:
        """Create the dialog box widget."""
        if not self.ui_manager:
            return

        self._dialog_box = DialogBox(width=600, height=140, position="bottom")
        self.ui_manager.add_widget(self._dialog_box)
        self._dialog_box.focus()

    def _update_dialog_box(self, context: DialogContext) -> None:
        """Update dialog box from context."""
        if not self._dialog_box:
            return

        self._dialog_box.set_text(
            context.displayed_text,
            speaker=context.speaker_name,
            portrait=context.portrait,
        )

        # Show choice menu if in choice state
        if context.state == DialogState.CHOICE_OPEN:
            self._show_choice_menu(context)

    def _destroy_dialog_box(self) -> None:
        """Remove dialog box widget."""
        if self._dialog_box and self.ui_manager:
            self.ui_manager.remove_widget(self._dialog_box)
            self._dialog_box = None

        self._hide_choice_menu()

    def _show_choice_menu(self, context: DialogContext) -> None:
        """Show choice menu with current choices."""
        if not self.ui_manager or not context.choices:
            return

        # Get choice texts, handling disabled choices
        choice_texts = []
        for choice in context.choices:
            if choice.condition:
                try:
                    if not eval(choice.condition, {"context": context}):
                        choice_texts.append(choice.disabled_text or "(unavailable)")
                        continue
                except Exception:
                    pass
            choice_texts.append(choice.text)

        if self._choice_menu:
            self._choice_menu.set_choices(choice_texts)
        else:
            self._choice_menu = ChoiceMenu(choices=choice_texts)
            self._choice_menu.set_allow_cancel(False)
            self._choice_menu.on_select = self._on_choice_selected
            self.ui_manager.add_widget(self._choice_menu)

        self._choice_menu.focus()

    def _update_choice_menu(self, context: DialogContext) -> None:
        """Update choice menu selection highlight."""
        # The choice menu handles its own focus navigation
        pass

    def _hide_choice_menu(self) -> None:
        """Hide and remove choice menu."""
        if self._choice_menu and self.ui_manager:
            self.ui_manager.remove_widget(self._choice_menu)
            self._choice_menu = None

    def _on_choice_selected(self, index: int, text: str) -> None:
        """Callback when choice is selected via UI."""
        if not self._active_entity:
            return

        context = self._active_entity.try_get(DialogContext)
        if context:
            context.selected_choice = index
            self._select_choice(context)

    # System update

    def process_entity(self, entity: Entity, dt: float) -> None:
        """Process dialog for an entity."""
        context = entity.get(DialogContext)
        if not context.is_active:
            return

        prev_char_idx = int(context.char_index)
        context.update_typewriter(dt)
        new_char_idx = int(context.char_index)

        # Play text blip
        if new_char_idx > prev_char_idx:
            self._blip_counter += new_char_idx - prev_char_idx
            if self.text_blip_sound and self._blip_counter >= self.text_blip_interval:
                self._blip_counter = 0
                self.event_bus.publish(
                    AudioEvent.SFX_PLAYED,
                    sound=self.text_blip_sound,
                    category="ui",
                )

            # Publish text advanced event
            self.event_bus.publish(DialogEvent.TEXT_ADVANCED, char_index=new_char_idx)

        # Update UI
        if entity == self._active_entity:
            self._update_dialog_box(context)

            # Check for text completion
            if context.is_text_complete and context.state == DialogState.WAITING_INPUT:
                self.event_bus.publish(DialogEvent.TEXT_COMPLETED)

    def update(self, dt: float) -> None:
        """Update all dialog entities."""
        if not self.enabled:
            return

        # Handle input first
        self.handle_input()

        # Process entities
        for entity in self.get_entities():
            if entity.active:
                self.process_entity(entity, dt)

    # Speaker interaction

    def interact_with_speaker(self, player: Entity, speaker: Entity) -> bool:
        """
        Start dialog with a speaker entity.

        Args:
            player: Entity with DialogContext (usually player)
            speaker: Entity with DialogSpeaker component

        Returns:
            True if dialog started
        """
        speaker_comp = speaker.try_get(DialogSpeaker)
        if not speaker_comp or not speaker_comp.dialog_id:
            return False

        return self.start_dialog(player, speaker_comp.dialog_id)

    @property
    def is_dialog_active(self) -> bool:
        """Check if any dialog is currently active."""
        return self._active_entity is not None
