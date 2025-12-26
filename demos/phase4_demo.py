"""
Phase 4 Demo: JRPG Framework

Demonstrates:
- Player movement with collision
- NPC with patrol AI
- Dialog system
- Turn-based battle
- Inventory and items
- Quest tracking
- Save/load

Controls:
- Arrow keys: Move
- Enter/Space: Interact/Confirm
- Escape: Menu/Cancel
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pygame
from imgui_bundle import imgui

from engine.core import Game, GameConfig, Scene, World
from engine.core.events import EventBus, EngineEvent
from engine.input.handler import InputHandler
from engine.core.actions import Action

# Framework imports
from framework.components import (
    Transform,
    Velocity,
    Direction,
    Health,
    Mana,
    CharacterStats,
    Experience,
    Inventory,
    DialogContext,
)
from framework.systems import MovementSystem, AISystem, InteractionSystem
from framework.world import create_player, create_npc, PlayerController
from framework.dialog import DialogManager
from framework.battle import BattleSystem, EnemyData, SkillData, TargetType
from framework.progression import QuestManager, SkillManager
from framework.save import SaveManager


class DemoScene(Scene):
    """Demo scene showing JRPG features."""

    def __init__(self, game: Game):
        super().__init__(game)
        self.world = World()
        self.events = EventBus()
        self.input = InputHandler()

        # Create player
        self.player = create_player(self.world, x=400, y=300, name="Hero")
        self.player_controller = PlayerController(self.player, self.input)

        # Create NPCs
        self.npc = create_npc(
            self.world, x=500, y=250,
            name="Villager",
            dialog_id="villager_intro",
        )

        # Systems
        self.movement_system = MovementSystem(self.world)
        self.ai_system = AISystem(self.world)
        self.ai_system.set_player(self.player)

        self.interaction_system = InteractionSystem(
            self.world, self.events, self.input
        )
        self.interaction_system.set_player(self.player)

        # Dialog
        self.dialog_manager = DialogManager(
            self.events, self.input,
            dialogs_path="game/data/dialog"
        )

        # Battle
        self.battle_system = BattleSystem(
            self.world, self.events, self.input
        )
        self._setup_battle_data()

        # Quest
        self.quest_manager = QuestManager()

        # Save
        self.save_manager = SaveManager(world=self.world)
        self.save_manager.set_quest_manager(self.quest_manager)

        # UI state
        self._show_debug = True
        self._show_menu = False
        self._in_battle = False

    def _setup_battle_data(self) -> None:
        """Setup battle enemies and skills."""
        # Register enemy type
        slime = EnemyData(
            id="slime",
            name="Slime",
            hp=30,
            strength=8,
            defense=5,
            agility=5,
            exp_reward=10,
            gold_reward=5,
        )
        self.battle_system.register_enemy(slime)

        # Register skills
        fire = SkillData(
            id="fire",
            name="Fire",
            description="Basic fire magic",
            mp_cost=5,
            power=120,
            is_magical=True,
            target_type=TargetType.SINGLE_ENEMY,
        )
        self.battle_system.register_skill(fire)

    def update(self, dt: float) -> None:
        # Process input events
        self.input.update(pygame.event.get())

        # Toggle debug
        if self.input.is_action_pressed(Action.DEBUG_TOGGLE):
            self._show_debug = not self._show_debug

        # Toggle menu
        if self.input.is_action_pressed(Action.MENU):
            self._show_menu = not self._show_menu

        # Update based on state
        if self._in_battle:
            self.battle_system.update(dt)
            if not self.battle_system.is_active:
                self._in_battle = False
        elif self.dialog_manager.is_active():
            self.dialog_manager.update(dt)
        elif not self._show_menu:
            # Normal gameplay
            self.player_controller.update(dt)
            self.movement_system.update(dt)
            self.ai_system.update(dt)
            self.interaction_system.update(dt)

        # Update save playtime
        self.save_manager.update_playtime(dt)

    def render(self) -> None:
        # Clear screen
        self.game.screen.fill((30, 40, 50))

        # Draw entities
        self._draw_entities()

        # Render ImGui
        self._render_imgui()

    def _draw_entities(self) -> None:
        """Draw all entities."""
        for entity_id in self.world.get_entities_with_components(Transform):
            entity = self.world.get_entity(entity_id)
            if not entity:
                continue

            transform = entity.get(Transform)
            if not transform:
                continue

            # Choose color based on tags
            if "player" in entity.tags:
                color = (100, 200, 100)
            elif "npc" in entity.tags:
                color = (100, 100, 200)
            else:
                color = (200, 200, 200)

            # Draw rectangle
            rect = pygame.Rect(
                int(transform.x) - 8,
                int(transform.y) - 8,
                16, 16
            )
            pygame.draw.rect(self.game.screen, color, rect)

            # Draw facing indicator
            vec = transform.facing.vector
            end_x = int(transform.x + vec[0] * 12)
            end_y = int(transform.y + vec[1] * 12)
            pygame.draw.line(
                self.game.screen,
                (255, 255, 255),
                (int(transform.x), int(transform.y)),
                (end_x, end_y),
                2
            )

    def _render_imgui(self) -> None:
        """Render ImGui overlays."""
        # Debug panel
        if self._show_debug:
            self._render_debug_panel()

        # Menu
        if self._show_menu:
            self._render_menu()

        # Battle UI
        if self._in_battle:
            self._render_battle_ui()

        # Dialog
        if self.dialog_manager.is_active():
            self._render_dialog()

    def _render_debug_panel(self) -> None:
        """Render debug information."""
        imgui.set_next_window_pos(imgui.ImVec2(10, 10))
        imgui.set_next_window_size(imgui.ImVec2(250, 300))

        if imgui.begin("Debug (F3)", None, imgui.WindowFlags_.no_collapse):
            # Player info
            transform = self.player.get(Transform)
            health = self.player.get(Health)
            mana = self.player.get(Mana)
            exp = self.player.get(Experience)

            imgui.text("=== Player ===")
            if transform:
                imgui.text(f"Position: ({transform.x:.0f}, {transform.y:.0f})")
                imgui.text(f"Facing: {transform.facing.name}")

            if health:
                imgui.text(f"HP: {health.current}/{health.max_hp}")
            if mana:
                imgui.text(f"MP: {mana.current}/{mana.max_mp}")
            if exp:
                imgui.text(f"Level: {exp.level}")
                imgui.text(f"EXP: {exp.current}/{exp.to_next_level}")

            imgui.separator()

            # Entity count
            entity_count = len(list(self.world.get_entities_with_components(Transform)))
            imgui.text(f"Entities: {entity_count}")

            imgui.separator()

            # Controls
            imgui.text("=== Controls ===")
            imgui.text("Arrows: Move")
            imgui.text("Enter: Interact")
            imgui.text("Esc: Menu")
            imgui.text("B: Start Battle")
            imgui.text("F5: Quick Save")
            imgui.text("F9: Quick Load")

            imgui.separator()

            # Actions
            if imgui.button("Start Battle"):
                self._start_demo_battle()

            if imgui.button("Save Game"):
                if self.save_manager.save_game(0, "Demo Save"):
                    print("Game saved!")

            if imgui.button("Load Game"):
                if self.save_manager.load_game(0):
                    print("Game loaded!")

        imgui.end()

    def _render_menu(self) -> None:
        """Render game menu."""
        viewport = imgui.get_main_viewport()
        center = viewport.get_center()

        imgui.set_next_window_pos(center, imgui.Cond_.always, imgui.ImVec2(0.5, 0.5))
        imgui.set_next_window_size(imgui.ImVec2(300, 400))

        if imgui.begin("Menu", None, imgui.WindowFlags_.no_collapse):
            if imgui.button("Resume", imgui.ImVec2(-1, 40)):
                self._show_menu = False

            imgui.separator()

            if imgui.button("Inventory", imgui.ImVec2(-1, 40)):
                pass  # TODO

            if imgui.button("Equipment", imgui.ImVec2(-1, 40)):
                pass  # TODO

            if imgui.button("Skills", imgui.ImVec2(-1, 40)):
                pass  # TODO

            if imgui.button("Quests", imgui.ImVec2(-1, 40)):
                pass  # TODO

            imgui.separator()

            if imgui.button("Save Game", imgui.ImVec2(-1, 40)):
                self.save_manager.save_game(0, "Quick Save")
                print("Game saved!")

            if imgui.button("Load Game", imgui.ImVec2(-1, 40)):
                self.save_manager.load_game(0)
                print("Game loaded!")

            imgui.separator()

            if imgui.button("Quit", imgui.ImVec2(-1, 40)):
                self.game.quit()

        imgui.end()

    def _render_battle_ui(self) -> None:
        """Render battle interface."""
        viewport = imgui.get_main_viewport()
        screen_h = viewport.size.y

        # Battle command menu
        imgui.set_next_window_pos(imgui.ImVec2(20, screen_h - 180))
        imgui.set_next_window_size(imgui.ImVec2(150, 160))

        if imgui.begin("Commands", None, imgui.WindowFlags_.no_collapse):
            commands = ["Attack", "Skill", "Item", "Defend", "Flee"]
            for i, cmd in enumerate(commands):
                is_selected = (i == self.battle_system.menu_selection)
                if is_selected:
                    imgui.push_style_color(imgui.Col_.text, imgui.ImVec4(1, 0.9, 0.5, 1))
                imgui.text(f"{'>' if is_selected else ' '} {cmd}")
                if is_selected:
                    imgui.pop_style_color()

        imgui.end()

        # Party status
        imgui.set_next_window_pos(imgui.ImVec2(viewport.size.x - 220, screen_h - 120))
        imgui.set_next_window_size(imgui.ImVec2(200, 100))

        if imgui.begin("Party", None, imgui.WindowFlags_.no_collapse):
            for actor in self.battle_system.party:
                imgui.text(f"{actor.name}")
                imgui.text(f"  HP: {actor.current_hp}/{actor.max_hp}")
                if actor.max_mp > 0:
                    imgui.text(f"  MP: {actor.current_mp}/{actor.max_mp}")

        imgui.end()

    def _render_dialog(self) -> None:
        """Render dialog box."""
        context = self.dialog_manager.get_context()
        if not context:
            return

        viewport = imgui.get_main_viewport()
        screen_w = viewport.size.x
        screen_h = viewport.size.y

        box_h = 150
        margin = 20

        imgui.set_next_window_pos(imgui.ImVec2(margin, screen_h - box_h - margin))
        imgui.set_next_window_size(imgui.ImVec2(screen_w - margin * 2, box_h))

        flags = (
            imgui.WindowFlags_.no_title_bar |
            imgui.WindowFlags_.no_resize |
            imgui.WindowFlags_.no_move
        )

        if imgui.begin("Dialog", None, flags):
            if context.speaker_name:
                imgui.text_colored(imgui.ImVec4(1, 0.9, 0.5, 1), context.speaker_name)
                imgui.separator()

            imgui.text_wrapped(context.displayed_text)

            if context.is_text_complete and not context.choices:
                imgui.text("...")

        imgui.end()

    def _start_demo_battle(self) -> None:
        """Start a demo battle."""
        self.battle_system.start_battle(
            party_entities=[self.player],
            enemy_types=["slime", "slime"],
            can_flee=True,
        )
        self._in_battle = True

    def on_enter(self) -> None:
        print("Phase 4 Demo Started")
        print("=" * 50)
        print("Features demonstrated:")
        print("  - Player movement (Arrow keys)")
        print("  - Entity system with components")
        print("  - Movement and AI systems")
        print("  - Dialog system (placeholder)")
        print("  - Battle system (press B)")
        print("  - Save/Load (F5/F9)")
        print("  - ImGui debug panel (F3)")
        print("=" * 50)

    def on_exit(self) -> None:
        print("Exiting demo...")


def main():
    """Run the Phase 4 demo."""
    # Configure game
    config = GameConfig(
        title="JRPG Framework - Phase 4 Demo",
        width=800,
        height=600,
        target_fps=60,
        vsync=True,
    )

    # Create game
    game = Game(config)

    # Create and push demo scene
    demo = DemoScene(game)
    game.scene_manager.push(demo)

    # Run
    game.run()


if __name__ == "__main__":
    main()
