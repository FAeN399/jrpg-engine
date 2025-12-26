"""
Battle UI Controller - connects BattleSystem to BattleHUD.

Manages the flow of UI updates during battle, handling:
- Party/enemy status display
- Command menu interaction
- Target selection
- Battle messages and animations
- Victory/defeat screens
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional, Callable, Any

from engine.core.events import EventBus, Event
from engine.core.actions import Action
from engine.ui.presets.battle_hud import BattleHUD, BattleActor as HUDBattleActor, BattleCommand as HUDBattleCommand

from framework.battle.system import (
    BattleSystem,
    BattleState,
    CommandMenu,
    BattleRewards,
)
from framework.battle.actor import BattleActor

if TYPE_CHECKING:
    from engine.input.handler import InputHandler
    from engine.ui.manager import UIManager
    from framework.audio.controller import GameAudioController


class BattleEvent(Enum):
    """Battle-specific events."""
    BATTLE_STARTED = auto()
    BATTLE_ENDED = auto()
    TURN_STARTED = auto()
    TURN_ENDED = auto()
    COMMAND_SELECTED = auto()
    TARGET_SELECTED = auto()
    ACTION_STARTED = auto()
    ACTION_COMPLETED = auto()
    DAMAGE_DEALT = auto()
    HEALING_DONE = auto()
    STATUS_APPLIED = auto()
    STATUS_REMOVED = auto()
    ACTOR_DEFEATED = auto()
    CRITICAL_HIT = auto()
    MISS = auto()
    VICTORY = auto()
    DEFEAT = auto()
    FLED = auto()


@dataclass
class TargetCursor:
    """Target selection state."""
    active: bool = False
    targeting_enemies: bool = True
    index: int = 0
    valid_targets: list[BattleActor] = None

    def __post_init__(self):
        if self.valid_targets is None:
            self.valid_targets = []


class BattleUIController:
    """
    Controller that bridges BattleSystem and BattleHUD.

    Responsibilities:
    - Create and manage BattleHUD widget
    - Update HUD from BattleSystem state
    - Handle UI input and feed commands to BattleSystem
    - Display battle messages and results
    - Trigger audio/animation events

    Usage:
        battle_ui = BattleUIController(battle_system, event_bus, input_handler, ui_manager)
        battle_ui.set_audio_controller(audio_ctrl)

        # In game loop
        battle_ui.update(dt)
    """

    def __init__(
        self,
        battle_system: BattleSystem,
        event_bus: EventBus,
        input_handler: InputHandler,
        ui_manager: UIManager,
    ):
        self.battle = battle_system
        self.event_bus = event_bus
        self.input = input_handler
        self.ui_manager = ui_manager

        # UI
        self._hud: Optional[BattleHUD] = None
        self._target_cursor = TargetCursor()

        # State
        self._last_state: Optional[BattleState] = None
        self._message_timer: float = 0.0
        self._message_duration: float = 1.5
        self._animation_playing: bool = False

        # Audio
        self._audio: Optional[GameAudioController] = None

        # Callbacks
        self._on_victory: Optional[Callable[[BattleRewards], None]] = None
        self._on_defeat: Optional[Callable[[], None]] = None

        # Result display
        self._showing_results: bool = False
        self._result_timer: float = 0.0
        self._result_duration: float = 3.0

    def set_audio_controller(self, audio: GameAudioController) -> None:
        """Set audio controller for battle sounds."""
        self._audio = audio

    def on_victory(self, callback: Callable[[BattleRewards], None]) -> None:
        """Set victory callback."""
        self._on_victory = callback

    def on_defeat(self, callback: Callable[[], None]) -> None:
        """Set defeat callback."""
        self._on_defeat = callback

    # Lifecycle

    def start(self) -> None:
        """Initialize battle UI."""
        if self._hud:
            return

        # Create HUD
        self._hud = BattleHUD()
        self._hud.rect.width = 800  # Full screen width
        self._hud.rect.height = 600
        self._hud.on_command_select = self._on_command_selected

        self.ui_manager.add_widget(self._hud)

        # Set up default commands
        self._setup_commands()

        # Initial state
        self._update_party_display()
        self._update_enemy_display()

        # Play battle start sound
        if self._audio:
            self._audio.on_battle_start()

        # Publish event
        self.event_bus.publish(
            BattleEvent.BATTLE_STARTED,
            party_count=len(self.battle.party),
            enemy_count=len(self.battle.enemies),
        )

    def end(self) -> None:
        """Clean up battle UI."""
        if self._hud:
            self.ui_manager.remove_widget(self._hud)
            self._hud = None

        self._target_cursor = TargetCursor()
        self._showing_results = False

    def update(self, dt: float) -> None:
        """Update battle UI."""
        if not self._hud or not self.battle.is_active:
            return

        # Check for state changes
        current_state = self.battle.state

        if current_state != self._last_state:
            self._on_state_change(self._last_state, current_state)
            self._last_state = current_state

        # Update message timer
        if self._message_timer > 0:
            self._message_timer -= dt
            if self._message_timer <= 0:
                self._hud.hide_message()

        # Update result screen timer
        if self._showing_results:
            self._result_timer -= dt
            if self._result_timer <= 0:
                self._finish_battle()

        # Handle input based on state
        if current_state == BattleState.PLAYER_INPUT:
            self._handle_command_input()
        elif current_state == BattleState.TARGET_SELECT:
            self._handle_target_input()

        # Refresh displays
        self._update_party_display()

    def _on_state_change(self, old_state: Optional[BattleState], new_state: BattleState) -> None:
        """Handle battle state transitions."""
        if new_state == BattleState.STARTING:
            self._show_message("Battle Start!")

        elif new_state == BattleState.TURN_START:
            actor = self.battle.current_actor
            if actor and actor.is_player_controlled:
                self._show_message(f"{actor.name}'s turn!")
                self.event_bus.publish(
                    BattleEvent.TURN_STARTED,
                    actor_name=actor.name,
                    is_player=True,
                )

        elif new_state == BattleState.PLAYER_INPUT:
            self._hud.show_commands(True)
            self._set_active_actor()

        elif new_state == BattleState.TARGET_SELECT:
            self._start_target_selection()

        elif new_state == BattleState.EXECUTING:
            self._hud.show_commands(False)
            self._hide_target_cursor()

        elif new_state == BattleState.VICTORY:
            self._on_battle_victory()

        elif new_state == BattleState.DEFEAT:
            self._on_battle_defeat()

        elif new_state == BattleState.FLED:
            self._on_battle_fled()

    # Command handling

    def _setup_commands(self) -> None:
        """Set up battle command menu."""
        commands = [
            HUDBattleCommand(id="attack", name="Attack"),
            HUDBattleCommand(id="skill", name="Skill"),
            HUDBattleCommand(id="item", name="Item"),
            HUDBattleCommand(id="defend", name="Defend"),
            HUDBattleCommand(id="flee", name="Flee"),
        ]
        self._hud.set_commands(commands)

    def _on_command_selected(self, command_id: str) -> None:
        """Handle command selection from HUD."""
        # Map command to menu enum
        command_map = {
            "attack": CommandMenu.ATTACK,
            "skill": CommandMenu.SKILL,
            "item": CommandMenu.ITEM,
            "defend": CommandMenu.DEFEND,
            "flee": CommandMenu.FLEE,
        }

        menu_cmd = command_map.get(command_id)
        if menu_cmd:
            # Simulate the battle system's menu selection
            self.battle._current_menu = menu_cmd
            self.battle._select_menu_command()

            self.event_bus.publish(
                BattleEvent.COMMAND_SELECTED,
                command=command_id,
            )

    def _handle_command_input(self) -> None:
        """Handle input during command selection."""
        if self.input.is_action_just_pressed(Action.MENU_UP):
            self._hud.navigate(-1, 0)
            if self._audio:
                self._audio.play_sound(self._audio.config.sfx.get("UI_CURSOR", ""), category="ui")

        elif self.input.is_action_just_pressed(Action.MENU_DOWN):
            self._hud.navigate(1, 0)
            if self._audio:
                self._audio.play_sound(self._audio.config.sfx.get("UI_CURSOR", ""), category="ui")

        elif self.input.is_action_just_pressed(Action.CONFIRM):
            self._hud.on_confirm()

    # Target selection

    def _start_target_selection(self) -> None:
        """Initialize target selection mode."""
        # Determine valid targets based on pending command
        cmd = self.battle._pending_command
        if not cmd:
            return

        if cmd.action_type.name in ("ATTACK", "SKILL"):
            # Target enemies by default
            self._target_cursor.targeting_enemies = True
            self._target_cursor.valid_targets = [e for e in self.battle.enemies if e.is_alive]
        else:
            # Target allies (items, some skills)
            self._target_cursor.targeting_enemies = False
            self._target_cursor.valid_targets = [a for a in self.battle.party if a.is_alive]

        self._target_cursor.index = 0
        self._target_cursor.active = True

        self._update_target_display()

    def _handle_target_input(self) -> None:
        """Handle input during target selection."""
        if not self._target_cursor.active:
            return

        targets = self._target_cursor.valid_targets
        if not targets:
            return

        if self.input.is_action_just_pressed(Action.MENU_LEFT):
            self._target_cursor.index = (self._target_cursor.index - 1) % len(targets)
            self._update_target_display()
            if self._audio:
                self._audio.play_sound(self._audio.config.sfx.get("UI_CURSOR", ""), category="ui")

        elif self.input.is_action_just_pressed(Action.MENU_RIGHT):
            self._target_cursor.index = (self._target_cursor.index + 1) % len(targets)
            self._update_target_display()
            if self._audio:
                self._audio.play_sound(self._audio.config.sfx.get("UI_CURSOR", ""), category="ui")

        elif self.input.is_action_just_pressed(Action.CONFIRM):
            self._confirm_target()

        elif self.input.is_action_just_pressed(Action.CANCEL):
            self._cancel_target_selection()

    def _update_target_display(self) -> None:
        """Update target cursor display."""
        if not self._target_cursor.valid_targets:
            return

        target = self._target_cursor.valid_targets[self._target_cursor.index]
        self._show_message(f"Target: {target.name}")

    def _confirm_target(self) -> None:
        """Confirm target selection."""
        if not self._target_cursor.valid_targets:
            return

        target = self._target_cursor.valid_targets[self._target_cursor.index]

        # Set target on pending command
        if self.battle._pending_command:
            self.battle._pending_command.targets = [target]
            self.battle.state = BattleState.EXECUTING

        self._target_cursor.active = False

        self.event_bus.publish(
            BattleEvent.TARGET_SELECTED,
            target_name=target.name,
            is_enemy=self._target_cursor.targeting_enemies,
        )

        # Play confirm sound
        if self._audio:
            self._audio.play_sound(self._audio.config.sfx.get("UI_CONFIRM", ""), category="ui")

    def _cancel_target_selection(self) -> None:
        """Cancel target selection and return to commands."""
        self._target_cursor.active = False
        self.battle._pending_command = None
        self.battle.state = BattleState.PLAYER_INPUT
        self._hud.hide_message()

        if self._audio:
            self._audio.play_sound(self._audio.config.sfx.get("UI_CANCEL", ""), category="ui")

    def _hide_target_cursor(self) -> None:
        """Hide target cursor."""
        self._target_cursor.active = False

    # Display updates

    def _update_party_display(self) -> None:
        """Update party status in HUD."""
        if not self._hud:
            return

        party_display = []
        for actor in self.battle.party:
            party_display.append(HUDBattleActor(
                name=actor.name[:8],  # Truncate long names
                hp=actor.current_hp,
                max_hp=actor.max_hp,
                mp=actor.current_mp,
                max_mp=actor.max_mp,
                is_player=actor.is_player_controlled,
                is_active=(actor == self.battle.current_actor),
            ))

        self._hud.set_party(party_display)

    def _update_enemy_display(self) -> None:
        """Update enemy display in HUD."""
        if not self._hud:
            return

        enemy_display = []
        for actor in self.battle.enemies:
            enemy_display.append(HUDBattleActor(
                name=actor.name,
                hp=actor.current_hp,
                max_hp=actor.max_hp,
                is_player=False,
            ))

        self._hud.set_enemies(enemy_display)

    def _set_active_actor(self) -> None:
        """Highlight the active actor in the party display."""
        if not self._hud or not self.battle.current_actor:
            return

        for i, actor in enumerate(self.battle.party):
            if actor == self.battle.current_actor:
                self._hud.set_active_actor(i)
                break

    # Messages

    def _show_message(self, text: str, duration: float = 1.5) -> None:
        """Show a battle message."""
        if self._hud:
            self._hud.show_message(text)
            self._message_timer = duration
            self._message_duration = duration

    # Battle end

    def _on_battle_victory(self) -> None:
        """Handle victory state."""
        self._show_message("Victory!", duration=2.0)
        self._showing_results = True
        self._result_timer = self._result_duration

        if self._audio:
            self._audio.on_battle_end(victory=True)

        self.event_bus.publish(BattleEvent.VICTORY)

    def _on_battle_defeat(self) -> None:
        """Handle defeat state."""
        self._show_message("Defeat...", duration=2.0)
        self._showing_results = True
        self._result_timer = self._result_duration

        if self._audio:
            self._audio.on_battle_end(victory=False)

        self.event_bus.publish(BattleEvent.DEFEAT)

    def _on_battle_fled(self) -> None:
        """Handle fled state."""
        self._show_message("Escaped!", duration=1.5)
        self._showing_results = True
        self._result_timer = 1.5

        self.event_bus.publish(BattleEvent.FLED)

    def _finish_battle(self) -> None:
        """Finish battle and trigger callbacks."""
        self._showing_results = False

        if self.battle.state == BattleState.VICTORY:
            # Calculate rewards
            rewards = BattleRewards()
            for enemy in self.battle.enemies:
                rewards.exp += 10  # Would come from enemy data
                rewards.gold += 5

            if self._on_victory:
                self._on_victory(rewards)

        elif self.battle.state == BattleState.DEFEAT:
            if self._on_defeat:
                self._on_defeat()

        # Clean up
        self.battle.end_battle()
        self.end()

    # Action result handling

    def show_action_result(
        self,
        actor_name: str,
        action_name: str,
        damage: int = 0,
        healing: int = 0,
        is_critical: bool = False,
        is_miss: bool = False,
    ) -> None:
        """Display action result message and play sounds."""
        if is_miss:
            self._show_message("Miss!")
            if self._audio:
                self._audio.on_miss()
            self.event_bus.publish(BattleEvent.MISS, actor=actor_name)

        elif damage > 0:
            if is_critical:
                self._show_message(f"Critical! {damage} damage!")
                if self._audio:
                    self._audio.on_hit(is_critical=True)
                self.event_bus.publish(BattleEvent.CRITICAL_HIT, damage=damage)
            else:
                self._show_message(f"{damage} damage!")
                if self._audio:
                    self._audio.on_hit(is_critical=False)

            self.event_bus.publish(
                BattleEvent.DAMAGE_DEALT,
                actor=actor_name,
                damage=damage,
            )

        elif healing > 0:
            self._show_message(f"Recovered {healing} HP!")
            self.event_bus.publish(
                BattleEvent.HEALING_DONE,
                actor=actor_name,
                healing=healing,
            )

    def show_actor_defeated(self, actor_name: str) -> None:
        """Display actor defeated message."""
        self._show_message(f"{actor_name} was defeated!")
        self.event_bus.publish(BattleEvent.ACTOR_DEFEATED, actor=actor_name)

    # Properties

    @property
    def is_active(self) -> bool:
        """Check if battle UI is active."""
        return self._hud is not None

    @property
    def is_showing_results(self) -> bool:
        """Check if showing battle results."""
        return self._showing_results
