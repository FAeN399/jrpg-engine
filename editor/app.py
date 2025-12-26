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
from engine.core.world import World
from engine.core.entity import Entity
from engine.graphics.tilemap import Tilemap, TileLayer
from editor.imgui_backend import ImGuiRenderer
from editor.panels.base import Panel, PanelManager
from editor.panels.map_editor import MapEditorPanel
from editor.panels.asset_browser import AssetBrowserPanel
from editor.panels.properties import PropertiesPanel
from editor.panels.scene_view import SceneViewPanel
from editor.panels.entity_hierarchy import EntityHierarchyPanel
from editor.panels.component_inspector import ComponentInspectorPanel
from editor.project import (
    ask_open_file, ask_save_file, ask_yes_no_cancel, show_info,
    ProjectData, tilemap_to_dict, tilemap_from_dict,
    world_to_dict, world_from_dict, save_project, load_project,
    PROJECT_FILETYPES,
)
from editor.asset_watcher import AssetWatcher, AssetEvent, AssetEventType

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

        # World reference (set when editing a scene)
        self.current_world: World | None = None

        # Tilemap for editing
        self.current_tilemap: Tilemap | None = None

        # Selection
        self.selected_entity_id: int | None = None
        self.selected_tile: tuple[int, int] | None = None
        self.selected_layer: str | None = "Ground"

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

    def create_new_tilemap(self, width: int = 32, height: int = 32, tile_size: int = 16) -> Tilemap:
        """Create a new tilemap for editing."""
        self.current_tilemap = Tilemap(width, height, tile_size)
        # Add default layers
        self.current_tilemap.add_layer("Ground")
        self.current_tilemap.add_layer("Decor")
        self.current_tilemap.add_layer("Objects")
        self.selected_layer = "Ground"
        self.grid_size = tile_size
        return self.current_tilemap

    def get_current_layer(self) -> TileLayer | None:
        """Get the currently selected tile layer."""
        if self.current_tilemap and self.selected_layer:
            return self.current_tilemap.get_layer(self.selected_layer)
        return None

    def get_selected_entity(self) -> Entity | None:
        """Get the currently selected entity from the world."""
        if self.current_world and self.selected_entity_id is not None:
            return self.current_world.get_entity(self.selected_entity_id)
        return None

    def select_entity(self, entity_id: int | None) -> None:
        """Select an entity by ID."""
        self.selected_entity_id = entity_id

    def clear_selection(self) -> None:
        """Clear all selections."""
        self.selected_entity_id = None
        self.selected_tile = None
        self.selected_layer = None

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
        self.asset_watcher: AssetWatcher | None = None

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
        self.panel_manager.add_panel(EntityHierarchyPanel(self.game, self.state))
        self.panel_manager.add_panel(ComponentInspectorPanel(self.game, self.state))

        # Create a default world for editing
        self.state.current_world = World()

        # Initialize asset watcher for hot reload
        self._setup_asset_watcher()

        print("Editor initialized!")
        print("Panels:", [p.title for p in self.panel_manager.panels])

    def on_exit(self) -> None:
        super().on_exit()

        # Stop asset watcher
        if self.asset_watcher:
            self.asset_watcher.stop()

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
                self._request_quit()

        ctrl = input.is_key_pressed(pygame.K_LCTRL) or input.is_key_pressed(pygame.K_RCTRL)
        shift = input.is_key_pressed(pygame.K_LSHIFT) or input.is_key_pressed(pygame.K_RSHIFT)

        # Ctrl+N to new project
        if ctrl and input.is_key_just_pressed(pygame.K_n):
            self._new_project()

        # Ctrl+O to open project
        if ctrl and input.is_key_just_pressed(pygame.K_o):
            self._open_project()

        # Ctrl+S to save, Ctrl+Shift+S to save as
        if ctrl and input.is_key_just_pressed(pygame.K_s):
            if shift:
                self._save_project_as()
            else:
                self._save_project()

        # Ctrl+Z to undo
        if ctrl and input.is_key_just_pressed(pygame.K_z):
            self._undo()

        # Ctrl+Y to redo
        if ctrl and input.is_key_just_pressed(pygame.K_y):
            self._redo()

        # Update panels
        if self.panel_manager:
            self.panel_manager.update(dt)

    def _request_quit(self) -> None:
        """Request to quit the editor, checking for unsaved changes."""
        if self._check_unsaved_changes():
            self.game.quit()

    # Asset hot reload

    def _setup_asset_watcher(self) -> None:
        """Initialize asset watcher for hot reload."""
        self.asset_watcher = AssetWatcher(debounce_seconds=0.5)
        self.asset_watcher.add_callback(self._on_asset_changed)

        # Watch common asset directories
        asset_dirs = ["assets", "sprites", "textures", "audio", "data"]
        for dir_name in asset_dirs:
            path = Path(dir_name)
            if path.exists():
                self.asset_watcher.watch(path)

        # Also watch project-relative paths
        if self.state.project_path:
            project_dir = self.state.project_path.parent
            for dir_name in asset_dirs:
                path = project_dir / dir_name
                if path.exists():
                    self.asset_watcher.watch(path)

        # Start watching
        if self.asset_watcher.is_available:
            self.asset_watcher.start()
        else:
            print("Note: Install 'watchdog' for faster hot reload")

    def _on_asset_changed(self, event: AssetEvent) -> None:
        """Handle asset file changes."""
        # Notify asset browser panel
        if self.panel_manager:
            for panel in self.panel_manager.panels:
                if hasattr(panel, 'notify_asset_changed'):
                    panel.notify_asset_changed(event.path)

        # Only handle modifications for now
        if event.event_type not in (AssetEventType.MODIFIED, AssetEventType.CREATED):
            return

        # Handle image changes - reload texture
        if event.is_image:
            if hasattr(self.game, 'texture_manager'):
                try:
                    self.game.texture_manager.reload(event.path)
                    print(f"Hot reloaded texture: {event.path.name}")
                except Exception as e:
                    print(f"Failed to reload texture {event.path.name}: {e}")

        # Handle data file changes
        elif event.is_data:
            print(f"Data file changed: {event.path.name}")
            # Could trigger re-parsing of game data here

        # Handle audio changes
        elif event.is_audio:
            print(f"Audio file changed: {event.path.name}")
            # Could trigger audio cache reload here

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

    def _check_unsaved_changes(self) -> bool:
        """
        Check for unsaved changes and prompt user.

        Returns:
            True if safe to proceed, False if user cancelled
        """
        if not self.state.is_dirty:
            return True

        result = ask_yes_no_cancel(
            "Unsaved Changes",
            f"Project '{self.state.project_name}' has unsaved changes.\n\n"
            "Do you want to save before continuing?"
        )

        if result is None:
            # User cancelled
            return False
        elif result:
            # User wants to save
            return self._save_project()

        # User chose not to save - proceed anyway
        return True

    def _new_project(self) -> None:
        """Create a new project."""
        if not self._check_unsaved_changes():
            return

        # Reset state
        self.state.project_path = None
        self.state.project_name = "Untitled"
        self.state.current_tilemap = None
        self.state.selected_entity_id = None
        self.state.selected_tile = None
        self.state.selected_layer = "Ground"

        # Create fresh world
        if self.state.current_world:
            self.state.current_world.clear()
        self.state.current_world = World()

        self.state.mark_clean()
        print("New project created")

    def _open_project(self) -> None:
        """Open an existing project."""
        if not self._check_unsaved_changes():
            return

        # Show file dialog
        filepath = ask_open_file(
            title="Open Project",
            filetypes=PROJECT_FILETYPES,
            initial_dir=self.state.project_path.parent if self.state.project_path else None,
        )

        if not filepath:
            return

        # Load project data
        project_data = load_project(filepath)
        if not project_data:
            return

        # Apply to editor state
        self.state.project_path = filepath
        self.state.project_name = project_data.name
        self.state.grid_size = project_data.grid_size
        self.state.show_grid = project_data.show_grid
        self.state.show_collision = project_data.show_collision

        # Load tilemap
        if project_data.tilemap:
            self.state.current_tilemap = tilemap_from_dict(project_data.tilemap)
            if self.state.current_tilemap.layers:
                self.state.selected_layer = self.state.current_tilemap.layers[0].name
        else:
            self.state.current_tilemap = None

        # Load entities
        if self.state.current_world:
            self.state.current_world.clear()
        self.state.current_world = World()
        if project_data.entities:
            world_from_dict(self.state.current_world, project_data.entities)

        self.state.selected_entity_id = None
        self.state.selected_tile = None
        self.state.mark_clean()

        print(f"Project loaded: {filepath}")

    def _save_project(self) -> bool:
        """
        Save the current project.

        Returns:
            True if saved successfully, False otherwise
        """
        if self.state.project_path:
            return self._do_save(self.state.project_path)
        else:
            return self._save_project_as()

    def _save_project_as(self) -> bool:
        """
        Save project with new name.

        Returns:
            True if saved successfully, False otherwise
        """
        filepath = ask_save_file(
            title="Save Project As",
            filetypes=PROJECT_FILETYPES,
            initial_dir=self.state.project_path.parent if self.state.project_path else None,
            initial_file=self.state.project_name,
            default_extension=".jrpg",
        )

        if not filepath:
            return False

        return self._do_save(filepath)

    def _do_save(self, filepath: Path) -> bool:
        """
        Actually save the project to a file.

        Args:
            filepath: Path to save to

        Returns:
            True if successful
        """
        # Build project data
        project_data = ProjectData(
            name=self.state.project_name or filepath.stem,
            grid_size=self.state.grid_size,
            show_grid=self.state.show_grid,
            show_collision=self.state.show_collision,
        )

        # Serialize tilemap
        if self.state.current_tilemap:
            project_data.tilemap = tilemap_to_dict(self.state.current_tilemap)

        # Serialize entities
        if self.state.current_world:
            project_data.entities = world_to_dict(self.state.current_world)

        # Save to file
        if save_project(filepath, project_data):
            self.state.project_path = filepath
            self.state.project_name = filepath.stem
            self.state.mark_clean()
            print(f"Project saved: {filepath}")
            return True

        return False

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
