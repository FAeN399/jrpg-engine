"""
Asset Browser panel - browse and manage project assets.

Provides:
- File tree navigation
- Asset preview
- Drag-and-drop support
- Hot reload monitoring
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum, auto
import os

from imgui_bundle import imgui

from editor.panels.base import Panel

if TYPE_CHECKING:
    from engine.core import Game
    from editor.app import EditorState


class AssetType(Enum):
    """Types of assets."""
    FOLDER = auto()
    IMAGE = auto()
    AUDIO = auto()
    MAP = auto()
    DATA = auto()
    SCRIPT = auto()
    UNKNOWN = auto()


@dataclass
class AssetEntry:
    """Represents a file or folder in the asset browser."""
    name: str
    path: Path
    asset_type: AssetType
    is_directory: bool
    size: int = 0
    children: list['AssetEntry'] | None = None

    @property
    def icon(self) -> str:
        """Get icon character for this asset type."""
        icons = {
            AssetType.FOLDER: "[D]",
            AssetType.IMAGE: "[I]",
            AssetType.AUDIO: "[A]",
            AssetType.MAP: "[M]",
            AssetType.DATA: "[J]",
            AssetType.SCRIPT: "[P]",
            AssetType.UNKNOWN: "[?]",
        }
        return icons.get(self.asset_type, "[?]")


def get_asset_type(path: Path) -> AssetType:
    """Determine asset type from file extension."""
    if path.is_dir():
        return AssetType.FOLDER

    ext = path.suffix.lower()

    if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
        return AssetType.IMAGE
    elif ext in ['.wav', '.mp3', '.ogg', '.flac']:
        return AssetType.AUDIO
    elif ext in ['.json', '.yaml', '.yml']:
        return AssetType.DATA
    elif ext in ['.py']:
        return AssetType.SCRIPT
    elif ext in ['.tmx', '.tmj']:
        return AssetType.MAP
    else:
        return AssetType.UNKNOWN


class AssetBrowserPanel(Panel):
    """
    Asset browser for managing project files.
    """

    @property
    def title(self) -> str:
        return "Assets"

    def __init__(self, game: Game, state: EditorState):
        super().__init__(game, state)

        # Current path
        self._root_path = Path("game/assets")
        self._current_path = self._root_path
        self._selected_asset: AssetEntry | None = None

        # View settings
        self._show_hidden = False
        self._filter_text = ""
        self._view_mode = "grid"  # "grid" or "list"
        self._icon_size = 64

        # File tree cache
        self._tree: AssetEntry | None = None
        self._needs_refresh = True

    def update(self, dt: float) -> None:
        # TODO: Hot reload detection
        pass

    def _render_content(self) -> None:
        # Toolbar
        self._render_toolbar()

        imgui.separator()

        # Main content area with two columns
        avail = imgui.get_content_region_avail()

        # Left column: folder tree
        imgui.begin_child(
            "FolderTree",
            imgui.ImVec2(200, avail.y),
            imgui.ChildFlags_.borders
        )
        self._render_folder_tree()
        imgui.end_child()

        imgui.same_line()

        # Right column: file view
        imgui.begin_child(
            "FileView",
            imgui.ImVec2(0, avail.y),
            imgui.ChildFlags_.borders
        )
        self._render_file_view()
        imgui.end_child()

    def _render_toolbar(self) -> None:
        """Render the asset browser toolbar."""
        # Back button
        if imgui.button("<"):
            if self._current_path != self._root_path:
                self._current_path = self._current_path.parent
                self._needs_refresh = True

        imgui.same_line()

        # Current path display
        imgui.text(str(self._current_path.relative_to(self._root_path.parent)))

        imgui.same_line()

        # Refresh button
        if imgui.button("Refresh"):
            self._needs_refresh = True

        imgui.same_line()

        # View mode toggle
        if imgui.button("Grid" if self._view_mode == "list" else "List"):
            self._view_mode = "list" if self._view_mode == "grid" else "grid"

        # Filter input
        imgui.same_line()
        imgui.set_next_item_width(150)
        changed, self._filter_text = imgui.input_text_with_hint(
            "##filter", "Filter...", self._filter_text
        )

    def _render_folder_tree(self) -> None:
        """Render the folder tree on the left."""
        if self._needs_refresh or self._tree is None:
            self._refresh_tree()

        if self._tree:
            self._render_tree_node(self._tree)

    def _render_tree_node(self, entry: AssetEntry, depth: int = 0) -> None:
        """Render a single tree node."""
        if not entry.is_directory:
            return

        # Tree node flags
        flags = imgui.TreeNodeFlags_.open_on_arrow | imgui.TreeNodeFlags_.span_avail_width

        if entry.path == self._current_path:
            flags |= imgui.TreeNodeFlags_.selected

        if not entry.children:
            flags |= imgui.TreeNodeFlags_.leaf

        # Render node
        is_open = imgui.tree_node_ex(f"{entry.icon} {entry.name}", flags)

        # Handle click
        if imgui.is_item_clicked():
            self._current_path = entry.path
            self._needs_refresh = True

        # Render children
        if is_open:
            if entry.children:
                for child in entry.children:
                    if child.is_directory:
                        self._render_tree_node(child, depth + 1)
            imgui.tree_pop()

    def _render_file_view(self) -> None:
        """Render the file view on the right."""
        # Get files in current directory
        entries = self._get_directory_contents(self._current_path)

        # Apply filter
        if self._filter_text:
            filter_lower = self._filter_text.lower()
            entries = [e for e in entries if filter_lower in e.name.lower()]

        if self._view_mode == "grid":
            self._render_grid_view(entries)
        else:
            self._render_list_view(entries)

    def _render_grid_view(self, entries: list[AssetEntry]) -> None:
        """Render files as a grid of icons."""
        avail_width = imgui.get_content_region_avail().x
        icon_size = self._icon_size
        padding = 8
        cols = max(1, int(avail_width / (icon_size + padding)))

        for i, entry in enumerate(entries):
            if i > 0 and i % cols != 0:
                imgui.same_line()

            # Create a selectable button for each item
            imgui.push_id(i)

            cursor_pos = imgui.get_cursor_pos()
            is_selected = (self._selected_asset and
                          self._selected_asset.path == entry.path)

            # Background
            if is_selected:
                draw_list = imgui.get_window_draw_list()
                p = imgui.get_cursor_screen_pos()
                draw_list.add_rect_filled(
                    p,
                    imgui.ImVec2(p.x + icon_size, p.y + icon_size + 20),
                    imgui.get_color_u32(imgui.ImVec4(0.3, 0.5, 0.8, 0.5))
                )

            # Invisible button for selection
            imgui.invisible_button("##item", imgui.ImVec2(icon_size, icon_size + 20))

            if imgui.is_item_clicked():
                self._selected_asset = entry

            if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(imgui.MouseButton_.left):
                if entry.is_directory:
                    self._current_path = entry.path
                    self._needs_refresh = True
                else:
                    self._open_asset(entry)

            # Draw icon placeholder
            imgui.set_cursor_pos(cursor_pos)
            imgui.begin_group()

            # Icon background
            icon_color = self._get_type_color(entry.asset_type)
            draw_list = imgui.get_window_draw_list()
            p = imgui.get_cursor_screen_pos()
            draw_list.add_rect_filled(
                imgui.ImVec2(p.x + 4, p.y + 4),
                imgui.ImVec2(p.x + icon_size - 4, p.y + icon_size - 10),
                icon_color,
                4.0
            )

            # Icon text
            imgui.set_cursor_pos(imgui.ImVec2(cursor_pos.x + 4, cursor_pos.y + icon_size // 3))
            imgui.text(entry.icon)

            # Filename (truncated)
            imgui.set_cursor_pos(imgui.ImVec2(cursor_pos.x, cursor_pos.y + icon_size - 6))
            name = entry.name[:10] + "..." if len(entry.name) > 13 else entry.name
            imgui.text(name)

            imgui.end_group()

            # Tooltip with full name
            if imgui.is_item_hovered():
                imgui.set_tooltip(entry.name)

            imgui.pop_id()

    def _render_list_view(self, entries: list[AssetEntry]) -> None:
        """Render files as a list."""
        for i, entry in enumerate(entries):
            is_selected = (self._selected_asset and
                          self._selected_asset.path == entry.path)

            if imgui.selectable(f"{entry.icon} {entry.name}", is_selected)[0]:
                self._selected_asset = entry

            if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(imgui.MouseButton_.left):
                if entry.is_directory:
                    self._current_path = entry.path
                    self._needs_refresh = True
                else:
                    self._open_asset(entry)

    def _get_type_color(self, asset_type: AssetType) -> int:
        """Get color for asset type."""
        colors = {
            AssetType.FOLDER: imgui.ImVec4(0.5, 0.5, 0.3, 1.0),
            AssetType.IMAGE: imgui.ImVec4(0.3, 0.5, 0.3, 1.0),
            AssetType.AUDIO: imgui.ImVec4(0.5, 0.3, 0.5, 1.0),
            AssetType.MAP: imgui.ImVec4(0.3, 0.3, 0.5, 1.0),
            AssetType.DATA: imgui.ImVec4(0.5, 0.4, 0.3, 1.0),
            AssetType.SCRIPT: imgui.ImVec4(0.3, 0.5, 0.5, 1.0),
            AssetType.UNKNOWN: imgui.ImVec4(0.4, 0.4, 0.4, 1.0),
        }
        return imgui.get_color_u32(colors.get(asset_type, colors[AssetType.UNKNOWN]))

    def _refresh_tree(self) -> None:
        """Refresh the folder tree."""
        if not self._root_path.exists():
            self._root_path.mkdir(parents=True, exist_ok=True)

        self._tree = self._build_tree(self._root_path)
        self._needs_refresh = False

    def _build_tree(self, path: Path) -> AssetEntry:
        """Build tree structure for a directory."""
        entry = AssetEntry(
            name=path.name or str(path),
            path=path,
            asset_type=AssetType.FOLDER,
            is_directory=True,
            children=[]
        )

        try:
            for child_path in sorted(path.iterdir()):
                if child_path.name.startswith('.') and not self._show_hidden:
                    continue

                if child_path.is_dir():
                    child = self._build_tree(child_path)
                    entry.children.append(child)
        except PermissionError:
            pass

        return entry

    def _get_directory_contents(self, path: Path) -> list[AssetEntry]:
        """Get contents of a directory."""
        entries = []

        if not path.exists():
            return entries

        try:
            for child_path in sorted(path.iterdir()):
                if child_path.name.startswith('.') and not self._show_hidden:
                    continue

                try:
                    size = child_path.stat().st_size if child_path.is_file() else 0
                except OSError:
                    size = 0

                entry = AssetEntry(
                    name=child_path.name,
                    path=child_path,
                    asset_type=get_asset_type(child_path),
                    is_directory=child_path.is_dir(),
                    size=size,
                )
                entries.append(entry)
        except PermissionError:
            pass

        # Sort: directories first, then by name
        entries.sort(key=lambda e: (not e.is_directory, e.name.lower()))
        return entries

    def _open_asset(self, entry: AssetEntry) -> None:
        """Open an asset for editing."""
        print(f"Opening asset: {entry.path}")
        # TODO: Open in appropriate editor
