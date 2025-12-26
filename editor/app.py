"""
Editor application.

The main editor that integrates with the game engine.
Can be run standalone or embedded in the game.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable
from pathlib import Path

import pygame
from imgui_bundle import imgui

from engine.core import Game, GameConfig, Scene, Action
from editor.imgui_backend import ImGuiRenderer
from editor.panels.base import Panel, PanelManager
from editor.panels.map_editor import MapEditorPanel
from editor.panels.asset_browser import AssetBrowserPanel
from editor.panels.properties import PropertiesPanel
from editor.panels.scene_view import SceneViewPanel

if TYPE_CHECKING:
    pass


class EditorMode(Enum):
    """Editor operation modes."""
    EDIT = auto()      # Normal editing
    PLAY = auto()      # Testing the game
    PAUSED = auto()    # Game paused


@dataclass
class EditorConfig:
    """Editor configuration."""
    window_title: str = "JRPG Engine Editor"
    window_width: int = 1600
    window_height: int = 900
    recent_projects: list[str] = field(default_factory=list)
    theme: str = "dark"
    autosave_interval: float = 300.0  # seconds


class EditorState:
    """
    Global editor state.

    Tracks current project, selection, tool state, etc.
    """

    def __init__(self):
        self.mode = EditorMode.EDIT
        self.project_path: Path | None = None
        self.project_name: str = "Untitled"

        # Selection
        self.selected_entity_id: int | None = None
        self.selected_tile: tuple[int, int] | None = None
        self.selected_layer: str | None = None

        # Tools
        self.current_tool: str = "select"
        self.brush_tile: int = 0
        self.brush_size: int = 1

        # View
        self.show_grid: bool = True
        self.show_collision: bool = False
        self.snap_to_grid: bool = True
        self.grid_size: int = 16

        # Dirty flag
        self.is_dirty: bool = False

    def mark_dirty(self) -> None:
        """Mark project as having unsaved changes."""
        self.is_dirty = True

    def mark_clean(self) -> None:
        """Mark project as saved."""
        self.is_dirty = False


class EditorScene(Scene):
    """
    Main editor scene.

    Manages the ImGui interface and editor panels.
    """

    def __init__(self, game: Game, config: EditorConfig | None = None):
        super().__init__(game)
        self.config = config or EditorConfig()
        self.state = EditorState()

        # Will be initialized in on_enter
        self.imgui_renderer: ImGuiRenderer | None = None
        self.panel_manager: PanelManager | None = None

    def on_enter(self) -> None:
        super().on_enter()

        # Initialize ImGui
        self.imgui_renderer = ImGuiRenderer(
            self.game.ctx,
            (self.game.width, self.game.height)
        )

        # Setup ImGui style
        self._setup_style()

        # Initialize panel manager
        self.panel_manager = PanelManager(self.state)

        # Add default panels
        self.panel_manager.add_panel(SceneViewPanel(self.game, self.state))
        self.panel_manager.add_panel(MapEditorPanel(self.game, self.state))
        self.panel_manager.add_panel(AssetBrowserPanel(self.game, self.state))
        self.panel_manager.add_panel(PropertiesPanel(self.game, self.state))

        print("Editor initialized!")
        print("Panels:", [p.title for p in self.panel_manager.panels])

    def on_exit(self) -> None:
        super().on_exit()
        if self.imgui_renderer:
            self.imgui_renderer.shutdown()

    def on_resize(self, width: int, height: int) -> None:
        if self.imgui_renderer:
            self.imgui_renderer.resize(width, height)

    def handle_event(self, event: pygame.event.Event) -> bool:
        # Let ImGui process the event first
        if self.imgui_renderer:
            if self.imgui_renderer.process_event(event):
                return True  # ImGui consumed the event

        return False

    def update(self, dt: float) -> None:
        # Handle global shortcuts
        input = self.game.input

        if input.is_action_just_pressed(Action.CANCEL):
            if self.state.mode == EditorMode.PLAY:
                self.state.mode = EditorMode.EDIT
            else:
                # TODO: Show quit confirmation if dirty
                self.game.quit()

        # Ctrl+S to save
        if (input.is_key_pressed(pygame.K_LCTRL) and
            input.is_key_just_pressed(pygame.K_s)):
            self._save_project()

        # Ctrl+Z to undo
        if (input.is_key_pressed(pygame.K_LCTRL) and
            input.is_key_just_pressed(pygame.K_z)):
            self._undo()

        # Ctrl+Y to redo
        if (input.is_key_pressed(pygame.K_LCTRL) and
            input.is_key_just_pressed(pygame.K_y)):
            self._redo()

        # Update panels
        if self.panel_manager:
            self.panel_manager.update(dt)

    def render(self, alpha: float) -> None:
        ctx = self.game.ctx

        # Clear screen
        ctx.clear(0.15, 0.15, 0.18, 1.0)

        # Start ImGui frame
        if self.imgui_renderer:
            self.imgui_renderer.new_frame(1/60)

            # Render main menu
            self._render_main_menu()

            # Enable docking
            self._setup_dockspace()

            # Render panels
            if self.panel_manager:
                self.panel_manager.render()

            # Render status bar
            self._render_status_bar()

            # Demo window for testing
            # imgui.show_demo_window()

            # Finish ImGui frame
            self.imgui_renderer.render()

        pygame.display.flip()

    def _setup_style(self) -> None:
        """Setup ImGui visual style."""
        style = imgui.get_style()

        # Dark theme colors
        colors = style.colors

        colors[imgui.Col_.window_bg] = imgui.ImVec4(0.1, 0.1, 0.12, 1.0)
        colors[imgui.Col_.header] = imgui.ImVec4(0.2, 0.2, 0.25, 1.0)
        colors[imgui.Col_.header_hovered] = imgui.ImVec4(0.3, 0.3, 0.35, 1.0)
        colors[imgui.Col_.header_active] = imgui.ImVec4(0.25, 0.25, 0.3, 1.0)
        colors[imgui.Col_.button] = imgui.ImVec4(0.2, 0.2, 0.25, 1.0)
        colors[imgui.Col_.button_hovered] = imgui.ImVec4(0.3, 0.3, 0.35, 1.0)
        colors[imgui.Col_.button_active] = imgui.ImVec4(0.25, 0.4, 0.6, 1.0)
        colors[imgui.Col_.frame_bg] = imgui.ImVec4(0.15, 0.15, 0.18, 1.0)
        colors[imgui.Col_.frame_bg_hovered] = imgui.ImVec4(0.2, 0.2, 0.25, 1.0)
        colors[imgui.Col_.frame_bg_active] = imgui.ImVec4(0.25, 0.25, 0.3, 1.0)
        colors[imgui.Col_.title_bg] = imgui.ImVec4(0.1, 0.1, 0.12, 1.0)
        colors[imgui.Col_.title_bg_active] = imgui.ImVec4(0.15, 0.15, 0.18, 1.0)
        colors[imgui.Col_.tab] = imgui.ImVec4(0.15, 0.15, 0.18, 1.0)
        colors[imgui.Col_.tab_hovered] = imgui.ImVec4(0.3, 0.3, 0.35, 1.0)
        colors[imgui.Col_.tab_selected] = imgui.ImVec4(0.2, 0.2, 0.25, 1.0)

        # Rounding
        style.window_rounding = 4.0
        style.frame_rounding = 2.0
        style.grab_rounding = 2.0
        style.tab_rounding = 4.0

        # Padding
        style.window_padding = imgui.ImVec2(8, 8)
        style.frame_padding = imgui.ImVec2(4, 3)
        style.item_spacing = imgui.ImVec2(8, 4)

    def _setup_dockspace(self) -> None:
        """Setup the main dockspace."""
        viewport = imgui.get_main_viewport()

        # Set window position and size to cover viewport (minus menu bar)
        imgui.set_next_window_pos(imgui.ImVec2(viewport.pos.x, viewport.pos.y + 20))
        imgui.set_next_window_size(imgui.ImVec2(viewport.size.x, viewport.size.y - 40))
        imgui.set_next_window_viewport(viewport.id_)

        # Window flags for dockspace host
        window_flags = (
            imgui.WindowFlags_.no_title_bar |
            imgui.WindowFlags_.no_collapse |
            imgui.WindowFlags_.no_resize |
            imgui.WindowFlags_.no_move |
            imgui.WindowFlags_.no_bring_to_front_on_focus |
            imgui.WindowFlags_.no_nav_focus |
            imgui.WindowFlags_.no_background
        )

        imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2(0, 0))
        imgui.begin("DockSpaceHost", None, window_flags)
        imgui.pop_style_var()

        # Create dockspace
        dockspace_id = imgui.get_id("EditorDockSpace")
        imgui.dock_space(dockspace_id, imgui.ImVec2(0, 0), imgui.DockNodeFlags_.none)

        imgui.end()

    def _render_main_menu(self) -> None:
        """Render the main menu bar."""
        if imgui.begin_main_menu_bar():
            # File menu
            if imgui.begin_menu("File"):
                if imgui.menu_item("New Project", "Ctrl+N")[0]:
                    self._new_project()
                if imgui.menu_item("Open Project", "Ctrl+O")[0]:
                    self._open_project()
                if imgui.menu_item("Save", "Ctrl+S", selected=False,
                                  enabled=self.state.is_dirty)[0]:
                    self._save_project()
                if imgui.menu_item("Save As...", "Ctrl+Shift+S")[0]:
                    self._save_project_as()
                imgui.separator()
                if imgui.menu_item("Exit", "Alt+F4")[0]:
                    self.game.quit()
                imgui.end_menu()

            # Edit menu
            if imgui.begin_menu("Edit"):
                if imgui.menu_item("Undo", "Ctrl+Z")[0]:
                    self._undo()
                if imgui.menu_item("Redo", "Ctrl+Y")[0]:
                    self._redo()
                imgui.separator()
                if imgui.menu_item("Cut", "Ctrl+X")[0]:
                    pass
                if imgui.menu_item("Copy", "Ctrl+C")[0]:
                    pass
                if imgui.menu_item("Paste", "Ctrl+V")[0]:
                    pass
                imgui.end_menu()

            # View menu
            if imgui.begin_menu("View"):
                if self.panel_manager:
                    for panel in self.panel_manager.panels:
                        changed, value = imgui.menu_item(
                            panel.title, "",
                            selected=panel.visible
                        )
                        if changed:
                            panel.visible = not panel.visible

                imgui.separator()
                _, self.state.show_grid = imgui.menu_item(
                    "Show Grid", "G", self.state.show_grid
                )
                _, self.state.show_collision = imgui.menu_item(
                    "Show Collision", "C", self.state.show_collision
                )
                imgui.end_menu()

            # Project menu
            if imgui.begin_menu("Project"):
                if imgui.menu_item("Run", "F5")[0]:
                    self._run_project()
                if imgui.menu_item("Build", "F6")[0]:
                    self._build_project()
                imgui.separator()
                if imgui.menu_item("Project Settings")[0]:
                    pass
                imgui.end_menu()

            # Help menu
            if imgui.begin_menu("Help"):
                if imgui.menu_item("Documentation")[0]:
                    pass
                if imgui.menu_item("About")[0]:
                    pass
                imgui.end_menu()

            imgui.end_main_menu_bar()

    def _render_status_bar(self) -> None:
        """Render the status bar at the bottom."""
        viewport = imgui.get_main_viewport()

        imgui.set_next_window_pos(imgui.ImVec2(
            viewport.pos.x,
            viewport.pos.y + viewport.size.y - 20
        ))
        imgui.set_next_window_size(imgui.ImVec2(viewport.size.x, 20))

        window_flags = (
            imgui.WindowFlags_.no_title_bar |
            imgui.WindowFlags_.no_resize |
            imgui.WindowFlags_.no_move |
            imgui.WindowFlags_.no_scrollbar |
            imgui.WindowFlags_.no_saved_settings
        )

        imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2(8, 2))
        imgui.begin("StatusBar", None, window_flags)
        imgui.pop_style_var()

        # Status text
        mode_text = {
            EditorMode.EDIT: "EDIT",
            EditorMode.PLAY: "PLAY",
            EditorMode.PAUSED: "PAUSED",
        }

        dirty_marker = "*" if self.state.is_dirty else ""
        status = f"{self.state.project_name}{dirty_marker} | Mode: {mode_text[self.state.mode]}"

        if self.state.selected_tile:
            status += f" | Tile: {self.state.selected_tile}"

        status += f" | Tool: {self.state.current_tool}"
        status += f" | FPS: {self.game.fps:.0f}"

        imgui.text(status)
        imgui.end()

    # Project operations

    def _new_project(self) -> None:
        """Create a new project."""
        self.state.project_path = None
        self.state.project_name = "Untitled"
        self.state.mark_clean()
        print("New project created")

    def _open_project(self) -> None:
        """Open an existing project."""
        # TODO: File dialog
        print("Open project (TODO: file dialog)")

    def _save_project(self) -> None:
        """Save the current project."""
        if self.state.project_path:
            # TODO: Actual save
            self.state.mark_clean()
            print(f"Project saved to {self.state.project_path}")
        else:
            self._save_project_as()

    def _save_project_as(self) -> None:
        """Save project with new name."""
        # TODO: File dialog
        print("Save project as (TODO: file dialog)")

    def _run_project(self) -> None:
        """Run the project in play mode."""
        self.state.mode = EditorMode.PLAY
        print("Running project...")

    def _build_project(self) -> None:
        """Build the project for distribution."""
        print("Building project...")

    def _undo(self) -> None:
        """Undo last action."""
        print("Undo")

    def _redo(self) -> None:
        """Redo last undone action."""
        print("Redo")


def run_editor(config: EditorConfig | None = None) -> None:
    """Run the editor as a standalone application."""
    config = config or EditorConfig()

    game_config = GameConfig(
        title=config.window_title,
        width=config.window_width,
        height=config.window_height,
        target_fps=60,
        resizable=True,
    )

    game = Game(game_config)
    game.scene_manager.push(EditorScene(game, config))
    game.run()


if __name__ == "__main__":
    run_editor()
