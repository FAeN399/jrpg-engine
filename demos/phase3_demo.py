"""
Phase 3 Demo: Editor Foundation

Demonstrates:
- ImGui integration with Pygame/ModernGL
- Dockable panel system
- Scene view with camera controls
- Map editor tools
- Asset browser
- Properties inspector

Controls:
- Use menu bar to toggle panels
- Middle mouse drag to pan scene view
- Scroll wheel to zoom
- Click tools in Map Editor panel
- Double-click folders in Asset Browser
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pygame
from imgui_bundle import imgui

from engine.core import Game, GameConfig
from editor.app import EditorScene


def main():
    """Run the Phase 3 editor demo."""
    # Configure game for editor
    config = GameConfig(
        title="JRPG Editor - Phase 3 Demo",
        width=1400,
        height=900,
        target_fps=60,
        vsync=True,
        resizable=True,
    )

    # Create game instance
    game = Game(config)

    # Create and push editor scene
    editor = EditorScene(game)
    game.scene_manager.push(editor)

    print("=" * 60)
    print("Phase 3 Demo: Editor Foundation")
    print("=" * 60)
    print()
    print("Features demonstrated:")
    print("  - ImGui integration with Pygame/ModernGL")
    print("  - Dockable panel system with layout persistence")
    print("  - Scene view with camera pan/zoom")
    print("  - Map editor with tool palette")
    print("  - Asset browser with folder navigation")
    print("  - Properties inspector for selected objects")
    print()
    print("Controls:")
    print("  - View menu: Toggle panels on/off")
    print("  - Scene View: Middle-drag to pan, scroll to zoom")
    print("  - Map Editor: Click tools, select tiles")
    print("  - Asset Browser: Double-click folders to navigate")
    print("  - Properties: Select items to inspect")
    print()
    print("Press ESC to exit")
    print("=" * 60)

    # Run!
    game.run()


if __name__ == "__main__":
    main()
