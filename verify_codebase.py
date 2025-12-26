"""
JRPG Engine Suite - Codebase Verification Script

This script verifies the integrity and functionality of the entire codebase.
Run this to check that all modules import correctly and basic functionality works.

Usage:
    python verify_codebase.py

Exit codes:
    0 - All tests passed
    1 - Some tests failed

For another agent reviewing this code:
    1. Run this script first to check import/structure issues
    2. Review any failures reported
    3. Check the file structure matches expected layout
    4. Verify dependencies are installed (pygame, moderngl, imgui-bundle, pydantic)
"""

import sys
import traceback
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field

# Ensure we're in the right directory
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    passed: bool
    message: str = ""
    error: Optional[str] = None


@dataclass
class TestSuite:
    """Collection of test results."""
    name: str
    results: list[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self) -> int:
        return len(self.results)


class CodebaseVerifier:
    """Verifies the JRPG engine codebase."""

    def __init__(self):
        self.suites: list[TestSuite] = []
        self.current_suite: Optional[TestSuite] = None

    def suite(self, name: str) -> None:
        """Start a new test suite."""
        self.current_suite = TestSuite(name=name)
        self.suites.append(self.current_suite)
        print(f"\n{'='*60}")
        print(f"  {name}")
        print(f"{'='*60}")

    def test(self, name: str, func: Callable[[], bool], message: str = "") -> bool:
        """Run a single test."""
        try:
            result = func()
            passed = bool(result)
            error = None
        except Exception as e:
            passed = False
            error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"

        test_result = TestResult(
            name=name,
            passed=passed,
            message=message,
            error=error,
        )

        if self.current_suite:
            self.current_suite.results.append(test_result)

        status = "PASS" if passed else "FAIL"
        icon = "✓" if passed else "✗"
        print(f"  [{status}] {icon} {name}")

        if error and not passed:
            # Print first line of error
            first_line = error.split('\n')[0]
            print(f"         └─ {first_line}")

        return passed

    def check_file_exists(self, path: str) -> bool:
        """Check if a file exists."""
        full_path = PROJECT_ROOT / path
        return full_path.exists()

    def check_import(self, module: str) -> bool:
        """Check if a module can be imported."""
        try:
            __import__(module)
            return True
        except ImportError as e:
            raise ImportError(f"Cannot import {module}: {e}")

    def print_summary(self) -> int:
        """Print summary and return exit code."""
        print("\n" + "="*60)
        print("  SUMMARY")
        print("="*60)

        total_passed = 0
        total_failed = 0

        for suite in self.suites:
            status = "PASS" if suite.failed == 0 else "FAIL"
            print(f"  [{status}] {suite.name}: {suite.passed}/{suite.total} passed")
            total_passed += suite.passed
            total_failed += suite.failed

        print("-"*60)
        print(f"  Total: {total_passed}/{total_passed + total_failed} tests passed")

        if total_failed > 0:
            print("\n  FAILURES:")
            for suite in self.suites:
                for result in suite.results:
                    if not result.passed:
                        print(f"    - {suite.name}/{result.name}")
                        if result.error:
                            print(f"      {result.error.split(chr(10))[0]}")

        print("="*60)

        return 0 if total_failed == 0 else 1


def main():
    """Run all verification tests."""
    v = CodebaseVerifier()

    # =========================================================================
    # FILE STRUCTURE
    # =========================================================================
    v.suite("File Structure - Engine Core")
    v.test("engine/__init__.py", lambda: v.check_file_exists("engine/__init__.py"))
    v.test("engine/core/__init__.py", lambda: v.check_file_exists("engine/core/__init__.py"))
    v.test("engine/core/game.py", lambda: v.check_file_exists("engine/core/game.py"))
    v.test("engine/core/scene.py", lambda: v.check_file_exists("engine/core/scene.py"))
    v.test("engine/core/entity.py", lambda: v.check_file_exists("engine/core/entity.py"))
    v.test("engine/core/component.py", lambda: v.check_file_exists("engine/core/component.py"))
    v.test("engine/core/system.py", lambda: v.check_file_exists("engine/core/system.py"))
    v.test("engine/core/world.py", lambda: v.check_file_exists("engine/core/world.py"))
    v.test("engine/core/events.py", lambda: v.check_file_exists("engine/core/events.py"))
    v.test("engine/core/actions.py", lambda: v.check_file_exists("engine/core/actions.py"))
    v.test("engine/input/handler.py", lambda: v.check_file_exists("engine/input/handler.py"))

    v.suite("File Structure - Engine Graphics")
    v.test("engine/graphics/__init__.py", lambda: v.check_file_exists("engine/graphics/__init__.py"))
    v.test("engine/graphics/context.py", lambda: v.check_file_exists("engine/graphics/context.py"))
    v.test("engine/graphics/texture.py", lambda: v.check_file_exists("engine/graphics/texture.py"))
    v.test("engine/graphics/batch.py", lambda: v.check_file_exists("engine/graphics/batch.py"))
    v.test("engine/graphics/tilemap.py", lambda: v.check_file_exists("engine/graphics/tilemap.py"))
    v.test("engine/graphics/camera.py", lambda: v.check_file_exists("engine/graphics/camera.py"))
    v.test("engine/graphics/lighting.py", lambda: v.check_file_exists("engine/graphics/lighting.py"))
    v.test("engine/graphics/particles.py", lambda: v.check_file_exists("engine/graphics/particles.py"))
    v.test("engine/graphics/postfx.py", lambda: v.check_file_exists("engine/graphics/postfx.py"))

    v.suite("File Structure - Editor")
    v.test("editor/__init__.py", lambda: v.check_file_exists("editor/__init__.py"))
    v.test("editor/app.py", lambda: v.check_file_exists("editor/app.py"))
    v.test("editor/imgui_backend.py", lambda: v.check_file_exists("editor/imgui_backend.py"))
    v.test("editor/panels/__init__.py", lambda: v.check_file_exists("editor/panels/__init__.py"))
    v.test("editor/panels/base.py", lambda: v.check_file_exists("editor/panels/base.py"))
    v.test("editor/panels/scene_view.py", lambda: v.check_file_exists("editor/panels/scene_view.py"))
    v.test("editor/panels/map_editor.py", lambda: v.check_file_exists("editor/panels/map_editor.py"))
    v.test("editor/panels/asset_browser.py", lambda: v.check_file_exists("editor/panels/asset_browser.py"))
    v.test("editor/panels/properties.py", lambda: v.check_file_exists("editor/panels/properties.py"))

    v.suite("File Structure - Framework Components")
    v.test("framework/__init__.py", lambda: v.check_file_exists("framework/__init__.py"))
    v.test("framework/components/__init__.py", lambda: v.check_file_exists("framework/components/__init__.py"))
    v.test("framework/components/transform.py", lambda: v.check_file_exists("framework/components/transform.py"))
    v.test("framework/components/physics.py", lambda: v.check_file_exists("framework/components/physics.py"))
    v.test("framework/components/character.py", lambda: v.check_file_exists("framework/components/character.py"))
    v.test("framework/components/combat.py", lambda: v.check_file_exists("framework/components/combat.py"))
    v.test("framework/components/inventory.py", lambda: v.check_file_exists("framework/components/inventory.py"))
    v.test("framework/components/dialog.py", lambda: v.check_file_exists("framework/components/dialog.py"))
    v.test("framework/components/ai.py", lambda: v.check_file_exists("framework/components/ai.py"))
    v.test("framework/components/interaction.py", lambda: v.check_file_exists("framework/components/interaction.py"))

    v.suite("File Structure - Framework Systems")
    v.test("framework/systems/__init__.py", lambda: v.check_file_exists("framework/systems/__init__.py"))
    v.test("framework/systems/movement.py", lambda: v.check_file_exists("framework/systems/movement.py"))
    v.test("framework/systems/collision.py", lambda: v.check_file_exists("framework/systems/collision.py"))
    v.test("framework/systems/ai.py", lambda: v.check_file_exists("framework/systems/ai.py"))
    v.test("framework/systems/interaction.py", lambda: v.check_file_exists("framework/systems/interaction.py"))

    v.suite("File Structure - Framework World")
    v.test("framework/world/__init__.py", lambda: v.check_file_exists("framework/world/__init__.py"))
    v.test("framework/world/map.py", lambda: v.check_file_exists("framework/world/map.py"))
    v.test("framework/world/player.py", lambda: v.check_file_exists("framework/world/player.py"))
    v.test("framework/world/npc.py", lambda: v.check_file_exists("framework/world/npc.py"))

    v.suite("File Structure - Framework Dialog")
    v.test("framework/dialog/__init__.py", lambda: v.check_file_exists("framework/dialog/__init__.py"))
    v.test("framework/dialog/system.py", lambda: v.check_file_exists("framework/dialog/system.py"))
    v.test("framework/dialog/parser.py", lambda: v.check_file_exists("framework/dialog/parser.py"))

    v.suite("File Structure - Framework Battle")
    v.test("framework/battle/__init__.py", lambda: v.check_file_exists("framework/battle/__init__.py"))
    v.test("framework/battle/actor.py", lambda: v.check_file_exists("framework/battle/actor.py"))
    v.test("framework/battle/actions.py", lambda: v.check_file_exists("framework/battle/actions.py"))
    v.test("framework/battle/system.py", lambda: v.check_file_exists("framework/battle/system.py"))

    v.suite("File Structure - Framework Progression")
    v.test("framework/progression/__init__.py", lambda: v.check_file_exists("framework/progression/__init__.py"))
    v.test("framework/progression/skills.py", lambda: v.check_file_exists("framework/progression/skills.py"))
    v.test("framework/progression/quests.py", lambda: v.check_file_exists("framework/progression/quests.py"))

    v.suite("File Structure - Framework Save")
    v.test("framework/save/__init__.py", lambda: v.check_file_exists("framework/save/__init__.py"))
    v.test("framework/save/manager.py", lambda: v.check_file_exists("framework/save/manager.py"))

    v.suite("File Structure - Framework Inventory")
    v.test("framework/inventory/__init__.py", lambda: v.check_file_exists("framework/inventory/__init__.py"))
    v.test("framework/inventory/items.py", lambda: v.check_file_exists("framework/inventory/items.py"))

    v.suite("File Structure - Demos")
    v.test("demos/phase1_demo.py", lambda: v.check_file_exists("demos/phase1_demo.py"))
    v.test("demos/phase2_demo.py", lambda: v.check_file_exists("demos/phase2_demo.py"))
    v.test("demos/phase3_demo.py", lambda: v.check_file_exists("demos/phase3_demo.py"))
    v.test("demos/phase4_demo.py", lambda: v.check_file_exists("demos/phase4_demo.py"))

    v.suite("File Structure - POC")
    v.test("poc/main.py", lambda: v.check_file_exists("poc/main.py"))

    # =========================================================================
    # MODULE IMPORTS
    # =========================================================================
    v.suite("Module Imports - Engine Core")
    v.test("import engine.core", lambda: v.check_import("engine.core"))
    v.test("import engine.core.game", lambda: v.check_import("engine.core.game"))
    v.test("import engine.core.scene", lambda: v.check_import("engine.core.scene"))
    v.test("import engine.core.entity", lambda: v.check_import("engine.core.entity"))
    v.test("import engine.core.component", lambda: v.check_import("engine.core.component"))
    v.test("import engine.core.system", lambda: v.check_import("engine.core.system"))
    v.test("import engine.core.world", lambda: v.check_import("engine.core.world"))
    v.test("import engine.core.events", lambda: v.check_import("engine.core.events"))
    v.test("import engine.core.actions", lambda: v.check_import("engine.core.actions"))
    v.test("import engine.input.handler", lambda: v.check_import("engine.input.handler"))

    v.suite("Module Imports - Engine Graphics")
    v.test("import engine.graphics", lambda: v.check_import("engine.graphics"))
    v.test("import engine.graphics.context", lambda: v.check_import("engine.graphics.context"))
    v.test("import engine.graphics.texture", lambda: v.check_import("engine.graphics.texture"))
    v.test("import engine.graphics.batch", lambda: v.check_import("engine.graphics.batch"))
    v.test("import engine.graphics.tilemap", lambda: v.check_import("engine.graphics.tilemap"))
    v.test("import engine.graphics.camera", lambda: v.check_import("engine.graphics.camera"))
    v.test("import engine.graphics.lighting", lambda: v.check_import("engine.graphics.lighting"))
    v.test("import engine.graphics.particles", lambda: v.check_import("engine.graphics.particles"))
    v.test("import engine.graphics.postfx", lambda: v.check_import("engine.graphics.postfx"))

    v.suite("Module Imports - Framework Components")
    v.test("import framework.components", lambda: v.check_import("framework.components"))
    v.test("import framework.components.transform", lambda: v.check_import("framework.components.transform"))
    v.test("import framework.components.physics", lambda: v.check_import("framework.components.physics"))
    v.test("import framework.components.character", lambda: v.check_import("framework.components.character"))
    v.test("import framework.components.combat", lambda: v.check_import("framework.components.combat"))
    v.test("import framework.components.inventory", lambda: v.check_import("framework.components.inventory"))
    v.test("import framework.components.dialog", lambda: v.check_import("framework.components.dialog"))
    v.test("import framework.components.ai", lambda: v.check_import("framework.components.ai"))
    v.test("import framework.components.interaction", lambda: v.check_import("framework.components.interaction"))

    v.suite("Module Imports - Framework Systems")
    v.test("import framework.systems", lambda: v.check_import("framework.systems"))
    v.test("import framework.systems.movement", lambda: v.check_import("framework.systems.movement"))
    v.test("import framework.systems.collision", lambda: v.check_import("framework.systems.collision"))
    v.test("import framework.systems.ai", lambda: v.check_import("framework.systems.ai"))
    v.test("import framework.systems.interaction", lambda: v.check_import("framework.systems.interaction"))

    v.suite("Module Imports - Framework World")
    v.test("import framework.world", lambda: v.check_import("framework.world"))
    v.test("import framework.world.map", lambda: v.check_import("framework.world.map"))
    v.test("import framework.world.player", lambda: v.check_import("framework.world.player"))
    v.test("import framework.world.npc", lambda: v.check_import("framework.world.npc"))

    v.suite("Module Imports - Framework Dialog")
    v.test("import framework.dialog", lambda: v.check_import("framework.dialog"))
    v.test("import framework.dialog.system", lambda: v.check_import("framework.dialog.system"))
    v.test("import framework.dialog.parser", lambda: v.check_import("framework.dialog.parser"))

    v.suite("Module Imports - Framework Battle")
    v.test("import framework.battle", lambda: v.check_import("framework.battle"))
    v.test("import framework.battle.actor", lambda: v.check_import("framework.battle.actor"))
    v.test("import framework.battle.actions", lambda: v.check_import("framework.battle.actions"))
    v.test("import framework.battle.system", lambda: v.check_import("framework.battle.system"))

    v.suite("Module Imports - Framework Progression")
    v.test("import framework.progression", lambda: v.check_import("framework.progression"))
    v.test("import framework.progression.skills", lambda: v.check_import("framework.progression.skills"))
    v.test("import framework.progression.quests", lambda: v.check_import("framework.progression.quests"))

    v.suite("Module Imports - Framework Save")
    v.test("import framework.save", lambda: v.check_import("framework.save"))
    v.test("import framework.save.manager", lambda: v.check_import("framework.save.manager"))

    v.suite("Module Imports - Framework Inventory")
    v.test("import framework.inventory", lambda: v.check_import("framework.inventory"))
    v.test("import framework.inventory.items", lambda: v.check_import("framework.inventory.items"))

    # =========================================================================
    # FUNCTIONALITY TESTS
    # =========================================================================
    v.suite("Functionality - Core Classes")

    def test_entity_creation():
        from engine.core import Entity
        e = Entity(1)
        e.name = "Test"
        e.tags.add("test")
        return e.id == 1 and e.name == "Test" and "test" in e.tags
    v.test("Entity creation", test_entity_creation)

    def test_world_creation():
        from engine.core import World
        w = World()
        e = w.create_entity()
        return e is not None and e.id in [eid for eid in w._entities]
    v.test("World creation", test_world_creation)

    def test_event_bus():
        from engine.core.events import EventBus, EngineEvent
        bus = EventBus()
        received = []
        bus.subscribe(EngineEvent.ENTITY_CREATED, lambda d: received.append(d))
        bus.emit(EngineEvent.ENTITY_CREATED, {"id": 1})
        return len(received) == 1 and received[0]["id"] == 1
    v.test("EventBus pub/sub", test_event_bus)

    def test_scene_manager():
        from engine.core.scene import SceneManager, Scene
        class TestScene(Scene):
            def update(self, dt): pass
            def render(self): pass
        sm = SceneManager()
        ts = TestScene(None)
        sm.push(ts)
        return sm.current == ts
    v.test("SceneManager", test_scene_manager)

    v.suite("Functionality - Components")

    def test_transform_component():
        from framework.components import Transform, Direction
        t = Transform(x=100, y=200, facing=Direction.UP)
        t.move(10, 20)
        return t.x == 110 and t.y == 220
    v.test("Transform component", test_transform_component)

    def test_health_component():
        from framework.components import Health
        h = Health(current=100, max_hp=100)
        dmg = h.take_damage(30)
        heal = h.heal(20)
        return h.current == 90 and dmg == 30 and heal == 20
    v.test("Health component", test_health_component)

    def test_inventory_component():
        from framework.components import Inventory
        inv = Inventory(max_slots=10)
        overflow = inv.add_item("potion", 5)
        has = inv.has_item("potion", 3)
        count = inv.count_item("potion")
        return overflow == 0 and has and count == 5
    v.test("Inventory component", test_inventory_component)

    def test_dialog_context():
        from framework.components import DialogContext, DialogState
        ctx = DialogContext()
        ctx.start_dialog("test", "start")
        return ctx.current_dialog_id == "test" and ctx.state == DialogState.STARTING
    v.test("DialogContext component", test_dialog_context)

    v.suite("Functionality - Battle System")

    def test_battle_actor():
        from framework.battle import BattleActor, ActorType
        from framework.components import CharacterStats, Health, CombatStats
        actor = BattleActor(
            entity_id=1,
            name="Hero",
            actor_type=ActorType.PLAYER,
            stats=CharacterStats(strength=15),
            health=Health(current=100, max_hp=100),
            mana=None,
            combat=CombatStats(),
        )
        return actor.is_alive and actor.get_attack() > 0
    v.test("BattleActor creation", test_battle_actor)

    def test_damage_calculation():
        from framework.battle import BattleActionExecutor, BattleActor, ActorType
        from framework.components import CharacterStats, Health, CombatStats

        attacker = BattleActor(
            entity_id=1, name="Attacker", actor_type=ActorType.PLAYER,
            stats=CharacterStats(strength=20),
            health=Health(100, 100), mana=None, combat=CombatStats(),
        )
        defender = BattleActor(
            entity_id=2, name="Defender", actor_type=ActorType.ENEMY,
            stats=CharacterStats(defense=10),
            health=Health(50, 50), mana=None, combat=CombatStats(),
        )

        executor = BattleActionExecutor()
        result = executor.execute_attack(attacker, [defender])
        return 2 in result.damage_dealt and result.damage_dealt[2] > 0
    v.test("Damage calculation", test_damage_calculation)

    v.suite("Functionality - Quest System")

    def test_quest_manager():
        from framework.progression import QuestManager, Quest, QuestObjective, ObjectiveType
        qm = QuestManager()
        # Manually add a quest template
        quest = Quest(
            id="test_quest",
            name="Test Quest",
            objectives=[
                QuestObjective(
                    id="obj1",
                    objective_type=ObjectiveType.KILL,
                    target_id="slime",
                    target_count=3,
                )
            ]
        )
        qm._quest_templates["test_quest"] = quest

        started = qm.start_quest("test_quest")
        updated = qm.update_objective(ObjectiveType.KILL, "slime", 3)
        active = qm.get_quest("test_quest")

        return started and "test_quest" in updated and active.is_complete
    v.test("Quest tracking", test_quest_manager)

    v.suite("Functionality - Save System")

    def test_save_manager():
        from framework.save import SaveManager
        sm = SaveManager(save_path="game/saves")
        sm.set_flag("test_flag", True)
        sm.set_flag("counter", 42)
        return sm.get_flag("test_flag") == True and sm.get_flag("counter") == 42
    v.test("SaveManager flags", test_save_manager)

    v.suite("Functionality - Dialog Parser")

    def test_dialog_parser():
        from framework.dialog import DialogParser

        script = """
# start
@Hero
Hello, world!
-> end

---

# end
@Hero
Goodbye!
"""
        parser = DialogParser()
        dialog = parser.parse_string(script)
        return len(dialog.nodes) == 2 and dialog.nodes[0].speaker == "Hero"
    v.test("Dialog script parsing", test_dialog_parser)

    # =========================================================================
    # DEPENDENCY CHECK
    # =========================================================================
    v.suite("Dependencies")

    def check_pygame():
        import pygame
        return pygame.version.ver is not None
    v.test("pygame installed", check_pygame)

    def check_moderngl():
        import moderngl
        return True
    v.test("moderngl installed", check_moderngl)

    def check_imgui():
        from imgui_bundle import imgui
        return True
    v.test("imgui-bundle installed", check_imgui)

    def check_numpy():
        import numpy
        return True
    v.test("numpy installed", check_numpy)

    # =========================================================================
    # SUMMARY
    # =========================================================================
    return v.print_summary()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║           JRPG ENGINE SUITE - CODEBASE VERIFICATION          ║
╠══════════════════════════════════════════════════════════════╣
║  This script verifies the integrity of the codebase.         ║
║                                                              ║
║  Phases verified:                                            ║
║    Phase 1: Core Engine (ECS, events, input)                 ║
║    Phase 2: GPU Rendering (ModernGL, shaders)                ║
║    Phase 3: Editor (ImGui, panels, tools)                    ║
║    Phase 4: JRPG Framework (battle, dialog, quests, etc.)    ║
╚══════════════════════════════════════════════════════════════╝
""")

    exit_code = main()

    if exit_code == 0:
        print("\n✓ All verification tests passed!")
        print("  The codebase is structurally sound.")
    else:
        print("\n✗ Some verification tests failed.")
        print("  Review the failures above and fix any issues.")

    sys.exit(exit_code)
