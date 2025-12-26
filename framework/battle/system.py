"""
Battle system - turn-based combat controller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Callable, Any
from enum import Enum, auto
import random

from engine.core import World, Entity
from engine.core.events import EventBus, EngineEvent
from engine.core.actions import Action
from framework.components import (
    CharacterStats,
    Health,
    Mana,
    CombatStats,
    Experience,
    Inventory,
)
from framework.battle.actor import BattleActor, ActorType, EnemyData, create_battle_actor_from_enemy
from framework.battle.actions import (
    BattleActionExecutor,
    ActionType,
    TargetType,
    ActionResult,
    SkillData,
    ItemData,
)

if TYPE_CHECKING:
    from engine.input.handler import InputHandler


class BattleState(Enum):
    """State of the battle."""
    NONE = auto()
    STARTING = auto()
    TURN_START = auto()
    PLAYER_INPUT = auto()
    TARGET_SELECT = auto()
    EXECUTING = auto()
    ANIMATION = auto()
    TURN_END = auto()
    VICTORY = auto()
    DEFEAT = auto()
    FLED = auto()
    ENDING = auto()


class CommandMenu(Enum):
    """Battle command menu selection."""
    ATTACK = auto()
    SKILL = auto()
    ITEM = auto()
    DEFEND = auto()
    FLEE = auto()


@dataclass
class BattleCommand:
    """A queued battle command."""
    actor: BattleActor
    action_type: ActionType
    skill_id: Optional[str] = None
    item_id: Optional[str] = None
    targets: list[BattleActor] = field(default_factory=list)


class TurnOrderManager:
    """Manages turn order for battle."""

    def __init__(self):
        self._actors: list[BattleActor] = []
        self._current_index: int = 0
        self._turn_count: int = 0

    def initialize(self, actors: list[BattleActor]) -> None:
        """Initialize turn order from actors."""
        self._actors = sorted(
            [a for a in actors if a.is_alive],
            key=lambda a: a.get_speed(),
            reverse=True,
        )
        self._current_index = 0
        self._turn_count = 1

    def get_current_actor(self) -> Optional[BattleActor]:
        """Get the current actor."""
        living = [a for a in self._actors if a.is_alive]
        if not living:
            return None

        while self._current_index < len(self._actors):
            actor = self._actors[self._current_index]
            if actor.is_alive:
                return actor
            self._current_index += 1

        return None

    def advance(self) -> Optional[BattleActor]:
        """Advance to next actor."""
        self._current_index += 1

        # Check if round is over
        if self._current_index >= len(self._actors):
            self._start_new_round()

        return self.get_current_actor()

    def _start_new_round(self) -> None:
        """Start a new round."""
        self._turn_count += 1
        self._current_index = 0

        # Re-sort by speed (might have changed)
        self._actors = sorted(
            [a for a in self._actors if a.is_alive],
            key=lambda a: a.get_speed(),
            reverse=True,
        )

    def remove_actor(self, actor: BattleActor) -> None:
        """Remove an actor from turn order."""
        # Don't actually remove, just mark as dead
        pass

    @property
    def turn_count(self) -> int:
        """Get current turn count."""
        return self._turn_count


@dataclass
class BattleRewards:
    """Rewards from winning a battle."""
    exp: int = 0
    gold: int = 0
    items: list[str] = field(default_factory=list)
    levels_gained: dict[int, int] = field(default_factory=dict)  # entity_id -> levels


class BattleSystem:
    """
    Turn-based battle controller.

    Manages:
    - Battle initialization
    - Turn order
    - Player input
    - Action execution
    - Win/lose conditions
    """

    def __init__(
        self,
        world: World,
        events: EventBus,
        input_handler: InputHandler,
    ):
        self.world = world
        self.events = events
        self.input = input_handler

        # State
        self.state = BattleState.NONE
        self._party: list[BattleActor] = []
        self._enemies: list[BattleActor] = []
        self._turn_order = TurnOrderManager()
        self._current_actor: Optional[BattleActor] = None

        # Input state
        self._menu_selection = 0
        self._skill_selection = 0
        self._item_selection = 0
        self._target_selection = 0
        self._current_menu = CommandMenu.ATTACK
        self._sub_menu_open = False

        # Current command being built
        self._pending_command: Optional[BattleCommand] = None

        # Action executor
        self._executor = BattleActionExecutor()

        # Callbacks
        self._on_battle_end: Optional[Callable[[BattleRewards], None]] = None

        # Enemy database
        self._enemy_database: dict[str, EnemyData] = {}

        # Available items (from party inventory)
        self._available_items: list[str] = []

    def register_enemy(self, enemy: EnemyData) -> None:
        """Register an enemy type."""
        self._enemy_database[enemy.id] = enemy

    def register_skill(self, skill: SkillData) -> None:
        """Register a skill."""
        self._executor.register_skill(skill)

    def register_item(self, item: ItemData) -> None:
        """Register an item."""
        self._executor.register_item(item)

    def start_battle(
        self,
        party_entities: list[Entity],
        enemy_types: list[str],
        can_flee: bool = True,
    ) -> bool:
        """
        Start a battle.

        Args:
            party_entities: Player party entities
            enemy_types: List of enemy type IDs
            can_flee: Whether fleeing is allowed

        Returns:
            True if battle started successfully
        """
        if self.state != BattleState.NONE:
            return False

        # Create party actors
        self._party.clear()
        for i, entity in enumerate(party_entities):
            actor = self._create_actor_from_entity(entity, i)
            if actor:
                self._party.append(actor)

        if not self._party:
            return False

        # Create enemy actors
        self._enemies.clear()
        entity_id_counter = 10000  # Temporary IDs for enemies
        for i, enemy_type in enumerate(enemy_types):
            enemy_data = self._enemy_database.get(enemy_type)
            if enemy_data:
                actor = create_battle_actor_from_enemy(
                    enemy_data,
                    entity_id_counter,
                    i,
                )
                self._enemies.append(actor)
                entity_id_counter += 1

        if not self._enemies:
            return False

        # Initialize turn order
        all_actors = self._party + self._enemies
        self._turn_order.initialize(all_actors)

        # Start battle
        self.state = BattleState.STARTING
        self._can_flee = can_flee

        # Emit event
        self.events.emit(EngineEvent.SCENE_TRANSITION, {
            'type': 'battle_start',
            'party_count': len(self._party),
            'enemy_count': len(self._enemies),
        })

        return True

    def _create_actor_from_entity(
        self,
        entity: Entity,
        position: int,
    ) -> Optional[BattleActor]:
        """Create a battle actor from an entity."""
        stats = entity.get(CharacterStats)
        health = entity.get(Health)

        if not stats or not health:
            return None

        mana = entity.get(Mana)
        combat = entity.get(CombatStats) or CombatStats()

        # Determine actor type
        if "player" in entity.tags:
            actor_type = ActorType.PLAYER
        elif "party_member" in entity.tags:
            actor_type = ActorType.PARTY_MEMBER
        else:
            actor_type = ActorType.PARTY_MEMBER

        return BattleActor(
            entity_id=entity.id,
            name=entity.name,
            actor_type=actor_type,
            stats=stats,
            health=health,
            mana=mana,
            combat=combat,
            position_index=position,
        )

    def update(self, dt: float) -> None:
        """Update battle system."""
        if self.state == BattleState.NONE:
            return

        if self.state == BattleState.STARTING:
            self._on_battle_start()

        elif self.state == BattleState.TURN_START:
            self._on_turn_start()

        elif self.state == BattleState.PLAYER_INPUT:
            self._handle_player_input()

        elif self.state == BattleState.TARGET_SELECT:
            self._handle_target_selection()

        elif self.state == BattleState.EXECUTING:
            self._execute_command()

        elif self.state == BattleState.TURN_END:
            self._on_turn_end()

        elif self.state in (BattleState.VICTORY, BattleState.DEFEAT, BattleState.FLED):
            self._on_battle_end()

        # Update status effect timers
        for actor in self._party + self._enemies:
            if actor.is_alive:
                actor.combat.update_effects(dt)

    def _on_battle_start(self) -> None:
        """Handle battle start."""
        # TODO: Play battle start animation
        self.state = BattleState.TURN_START

    def _on_turn_start(self) -> None:
        """Handle start of a turn."""
        self._current_actor = self._turn_order.get_current_actor()

        if not self._current_actor:
            # No one left to act, check win/lose
            self._check_battle_end()
            return

        self._current_actor.start_turn()

        # Check for status effects that prevent action
        if self._current_actor.has_status(StatusType.PARALYSIS):
            # Skip turn
            self.state = BattleState.TURN_END
            return

        if self._current_actor.has_status(StatusType.SLEEP):
            # Skip turn (might wake up on hit)
            self.state = BattleState.TURN_END
            return

        if self._current_actor.is_player_controlled:
            self.state = BattleState.PLAYER_INPUT
            self._menu_selection = 0
            self._sub_menu_open = False
        else:
            # Enemy AI
            self._execute_enemy_ai()

    def _handle_player_input(self) -> None:
        """Handle player input for command selection."""
        if self._sub_menu_open:
            # In skill or item submenu
            if self.input.is_action_pressed(Action.CANCEL):
                self._sub_menu_open = False
                return

            if self._current_menu == CommandMenu.SKILL:
                self._handle_skill_selection()
            elif self._current_menu == CommandMenu.ITEM:
                self._handle_item_selection()
            return

        # Main menu navigation
        if self.input.is_action_pressed(Action.MOVE_UP):
            self._menu_selection = (self._menu_selection - 1) % 5
        elif self.input.is_action_pressed(Action.MOVE_DOWN):
            self._menu_selection = (self._menu_selection + 1) % 5

        if self.input.is_action_pressed(Action.CONFIRM):
            self._select_menu_command()

    def _select_menu_command(self) -> None:
        """Select command from main menu."""
        commands = [
            CommandMenu.ATTACK,
            CommandMenu.SKILL,
            CommandMenu.ITEM,
            CommandMenu.DEFEND,
            CommandMenu.FLEE,
        ]
        self._current_menu = commands[self._menu_selection]

        if self._current_menu == CommandMenu.ATTACK:
            self._pending_command = BattleCommand(
                actor=self._current_actor,
                action_type=ActionType.ATTACK,
            )
            self._target_selection = 0
            self.state = BattleState.TARGET_SELECT

        elif self._current_menu == CommandMenu.SKILL:
            if self._current_actor.skills:
                self._skill_selection = 0
                self._sub_menu_open = True

        elif self._current_menu == CommandMenu.ITEM:
            # TODO: Get available items from inventory
            self._available_items = []  # Would come from inventory
            if self._available_items:
                self._item_selection = 0
                self._sub_menu_open = True

        elif self._current_menu == CommandMenu.DEFEND:
            self._pending_command = BattleCommand(
                actor=self._current_actor,
                action_type=ActionType.DEFEND,
            )
            self.state = BattleState.EXECUTING

        elif self._current_menu == CommandMenu.FLEE:
            if self._can_flee:
                self._pending_command = BattleCommand(
                    actor=self._current_actor,
                    action_type=ActionType.FLEE,
                )
                self.state = BattleState.EXECUTING

    def _handle_skill_selection(self) -> None:
        """Handle skill menu."""
        skills = self._current_actor.skills

        if self.input.is_action_pressed(Action.MOVE_UP):
            self._skill_selection = (self._skill_selection - 1) % len(skills)
        elif self.input.is_action_pressed(Action.MOVE_DOWN):
            self._skill_selection = (self._skill_selection + 1) % len(skills)

        if self.input.is_action_pressed(Action.CONFIRM):
            skill_id = skills[self._skill_selection]
            self._pending_command = BattleCommand(
                actor=self._current_actor,
                action_type=ActionType.SKILL,
                skill_id=skill_id,
            )
            self._sub_menu_open = False
            self._target_selection = 0
            self.state = BattleState.TARGET_SELECT

    def _handle_item_selection(self) -> None:
        """Handle item menu."""
        items = self._available_items

        if self.input.is_action_pressed(Action.MOVE_UP):
            self._item_selection = (self._item_selection - 1) % len(items)
        elif self.input.is_action_pressed(Action.MOVE_DOWN):
            self._item_selection = (self._item_selection + 1) % len(items)

        if self.input.is_action_pressed(Action.CONFIRM):
            item_id = items[self._item_selection]
            self._pending_command = BattleCommand(
                actor=self._current_actor,
                action_type=ActionType.ITEM,
                item_id=item_id,
            )
            self._sub_menu_open = False
            self._target_selection = 0
            self.state = BattleState.TARGET_SELECT

    def _handle_target_selection(self) -> None:
        """Handle target selection."""
        # Determine valid targets
        if self._pending_command.action_type == ActionType.ATTACK:
            targets = [e for e in self._enemies if e.is_alive]
        elif self._pending_command.action_type == ActionType.SKILL:
            # TODO: Get target type from skill
            targets = [e for e in self._enemies if e.is_alive]
        else:
            targets = [a for a in self._party if a.is_alive]

        if not targets:
            self.state = BattleState.PLAYER_INPUT
            return

        if self.input.is_action_pressed(Action.MOVE_LEFT):
            self._target_selection = (self._target_selection - 1) % len(targets)
        elif self.input.is_action_pressed(Action.MOVE_RIGHT):
            self._target_selection = (self._target_selection + 1) % len(targets)

        if self.input.is_action_pressed(Action.CONFIRM):
            self._pending_command.targets = [targets[self._target_selection]]
            self.state = BattleState.EXECUTING

        if self.input.is_action_pressed(Action.CANCEL):
            self._pending_command = None
            self.state = BattleState.PLAYER_INPUT

    def _execute_command(self) -> None:
        """Execute the pending command."""
        if not self._pending_command:
            self.state = BattleState.TURN_END
            return

        cmd = self._pending_command
        result: Optional[ActionResult] = None

        if cmd.action_type == ActionType.ATTACK:
            result = self._executor.execute_attack(cmd.actor, cmd.targets)

        elif cmd.action_type == ActionType.SKILL:
            result = self._executor.execute_skill(
                cmd.actor, cmd.skill_id, cmd.targets
            )

        elif cmd.action_type == ActionType.ITEM:
            result = self._executor.execute_item(
                cmd.actor, cmd.item_id, cmd.targets
            )

        elif cmd.action_type == ActionType.DEFEND:
            result = self._executor.execute_defend(cmd.actor)

        elif cmd.action_type == ActionType.FLEE:
            result = self._executor.execute_flee(self._party, self._enemies)
            if result.fled:
                self.state = BattleState.FLED
                return

        # Emit result event
        if result:
            self.events.emit(EngineEvent.ENTITY_MODIFIED, {
                'type': 'battle_action',
                'actor': cmd.actor.name,
                'action': cmd.action_type.name,
                'damage': result.damage_dealt,
                'healing': result.healing_done,
            })

        self._pending_command = None
        self.state = BattleState.TURN_END

    def _execute_enemy_ai(self) -> None:
        """Execute AI for enemy turn."""
        enemy = self._current_actor

        # Simple AI: pick random target and attack
        living_party = [a for a in self._party if a.is_alive]
        if not living_party:
            self._check_battle_end()
            return

        target = random.choice(living_party)

        self._pending_command = BattleCommand(
            actor=enemy,
            action_type=ActionType.ATTACK,
            targets=[target],
        )
        self.state = BattleState.EXECUTING

    def _on_turn_end(self) -> None:
        """Handle end of turn."""
        if self._current_actor:
            self._current_actor.end_turn()

        # Apply status damage (poison, burn, etc.)
        self._process_status_damage()

        # Check win/lose
        if self._check_battle_end():
            return

        # Advance to next actor
        self._turn_order.advance()
        self.state = BattleState.TURN_START

    def _process_status_damage(self) -> None:
        """Process damage from status effects."""
        for actor in self._party + self._enemies:
            if not actor.is_alive:
                continue

            # Poison
            if actor.has_status(StatusType.POISON):
                damage = max(1, actor.max_hp // 10)
                actor.health.take_damage(damage)

            # Burn
            if actor.has_status(StatusType.BURN):
                damage = max(1, actor.max_hp // 8)
                actor.health.take_damage(damage)

            # Regen
            if actor.has_status(StatusType.REGEN):
                heal = max(1, actor.max_hp // 10)
                actor.health.heal(heal)

    def _check_battle_end(self) -> bool:
        """Check if battle should end."""
        party_alive = any(a.is_alive for a in self._party)
        enemies_alive = any(e.is_alive for e in self._enemies)

        if not enemies_alive:
            self.state = BattleState.VICTORY
            return True

        if not party_alive:
            self.state = BattleState.DEFEAT
            return True

        return False

    def _on_battle_end(self) -> None:
        """Handle battle end."""
        rewards = BattleRewards()

        if self.state == BattleState.VICTORY:
            # Calculate rewards
            for enemy in self._enemies:
                # Would get from enemy data
                rewards.exp += 10
                rewards.gold += 5

            # Distribute EXP
            for actor in self._party:
                if actor.is_alive:
                    entity = self.world.get_entity(actor.entity_id)
                    if entity:
                        exp = entity.get(Experience)
                        if exp:
                            levels = exp.add_exp(rewards.exp)
                            if levels > 0:
                                rewards.levels_gained[actor.entity_id] = levels

        # Emit end event
        self.events.emit(EngineEvent.SCENE_TRANSITION, {
            'type': 'battle_end',
            'result': self.state.name,
            'rewards': {
                'exp': rewards.exp,
                'gold': rewards.gold,
                'items': rewards.items,
            },
        })

        # Call callback
        if self._on_battle_end:
            self._on_battle_end(rewards)

        self.state = BattleState.ENDING

    def end_battle(self) -> None:
        """Clean up and end battle."""
        self._party.clear()
        self._enemies.clear()
        self._pending_command = None
        self._current_actor = None
        self.state = BattleState.NONE

    def on_battle_end(self, callback: Callable[[BattleRewards], None]) -> None:
        """Set callback for battle end."""
        self._on_battle_end = callback

    @property
    def is_active(self) -> bool:
        """Check if battle is active."""
        return self.state != BattleState.NONE

    @property
    def party(self) -> list[BattleActor]:
        """Get party actors."""
        return self._party

    @property
    def enemies(self) -> list[BattleActor]:
        """Get enemy actors."""
        return self._enemies

    @property
    def current_actor(self) -> Optional[BattleActor]:
        """Get current acting entity."""
        return self._current_actor

    @property
    def menu_selection(self) -> int:
        """Get current menu selection."""
        return self._menu_selection

    @property
    def target_selection(self) -> int:
        """Get current target selection."""
        return self._target_selection
