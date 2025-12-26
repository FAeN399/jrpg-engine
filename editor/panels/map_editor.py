"""
Map Editor panel - tools and layers for tile editing.

Provides:
- Tile palette/picker
- Layer management
- Brush tools (paint, fill, rectangle, eraser)
- Tile properties
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from enum import Enum, auto

from imgui_bundle import imgui

from editor.panels.base import Panel

if TYPE_CHECKING:
    from engine.core import Game
    from editor.app import EditorState


class BrushTool(Enum):
    """Available brush tools."""
    SELECT = auto()
    BRUSH = auto()
    FILL = auto()
    RECTANGLE = auto()
    ERASER = auto()
    EYEDROPPER = auto()


class MapEditorPanel(Panel):
    """
    Map editing tools and tileset palette.
    """

    @property
    def title(self) -> str:
        return "Map Editor"

    def __init__(self, game: Game, state: EditorState):
        super().__init__(game, state)

        # Tool state
        self._current_tool = BrushTool.BRUSH
        self._brush_size = 1

        # Tileset display
        self._tileset_zoom = 2.0
        self._selected_tile = 0

        # Layer management
        self._layers = ["Ground", "Decor", "Objects"]
        self._selected_layer = 0
        self._layer_visibility = [True, True, True]

    def _render_content(self) -> None:
        # Tools section
        if imgui.collapsing_header("Tools", imgui.TreeNodeFlags_.default_open):
            self._render_tools()

        imgui.separator()

        # Brush settings
        if imgui.collapsing_header("Brush", imgui.TreeNodeFlags_.default_open):
            self._render_brush_settings()

        imgui.separator()

        # Layers section
        if imgui.collapsing_header("Layers", imgui.TreeNodeFlags_.default_open):
            self._render_layers()

        imgui.separator()

        # Tileset palette
        if imgui.collapsing_header("Tileset", imgui.TreeNodeFlags_.default_open):
            self._render_tileset()

    def _render_tools(self) -> None:
        """Render tool selection buttons."""
        button_size = imgui.ImVec2(32, 32)

        tools = [
            (BrushTool.SELECT, "S", "Select (V)"),
            (BrushTool.BRUSH, "B", "Brush (B)"),
            (BrushTool.FILL, "F", "Fill (G)"),
            (BrushTool.RECTANGLE, "R", "Rectangle (R)"),
            (BrushTool.ERASER, "E", "Eraser (E)"),
            (BrushTool.EYEDROPPER, "I", "Eyedropper (I)"),
        ]

        for i, (tool, label, tooltip) in enumerate(tools):
            if i > 0:
                imgui.same_line()

            # Highlight active tool
            if self._current_tool == tool:
                imgui.push_style_color(imgui.Col_.button,
                                       imgui.ImVec4(0.3, 0.5, 0.8, 1.0))

            if imgui.button(label, button_size):
                self._current_tool = tool
                self.state.current_tool = tool.name.lower()

            if self._current_tool == tool:
                imgui.pop_style_color()

            if imgui.is_item_hovered():
                imgui.set_tooltip(tooltip)

    def _render_brush_settings(self) -> None:
        """Render brush configuration."""
        # Brush size
        changed, value = imgui.slider_int(
            "Size", self._brush_size, 1, 10
        )
        if changed:
            self._brush_size = value
            self.state.brush_size = value

        # Grid snapping
        _, self.state.snap_to_grid = imgui.checkbox(
            "Snap to Grid", self.state.snap_to_grid
        )

    def _render_layers(self) -> None:
        """Render layer management."""
        # Layer list
        for i, layer_name in enumerate(self._layers):
            # Visibility toggle
            visible = self._layer_visibility[i]
            clicked, visible = imgui.checkbox(f"##vis_{i}", visible)
            if clicked:
                self._layer_visibility[i] = visible

            imgui.same_line()

            # Selectable layer name
            is_selected = (i == self._selected_layer)
            if imgui.selectable(layer_name, is_selected)[0]:
                self._selected_layer = i
                self.state.selected_layer = layer_name

        imgui.separator()

        # Layer controls
        if imgui.button("Add Layer"):
            new_name = f"Layer {len(self._layers)}"
            self._layers.append(new_name)
            self._layer_visibility.append(True)

        imgui.same_line()

        if imgui.button("Remove") and len(self._layers) > 1:
            if self._selected_layer < len(self._layers):
                self._layers.pop(self._selected_layer)
                self._layer_visibility.pop(self._selected_layer)
                if self._selected_layer >= len(self._layers):
                    self._selected_layer = len(self._layers) - 1

        # Move layer up/down
        imgui.same_line()
        if imgui.button("Up") and self._selected_layer > 0:
            i = self._selected_layer
            self._layers[i], self._layers[i-1] = self._layers[i-1], self._layers[i]
            self._layer_visibility[i], self._layer_visibility[i-1] = \
                self._layer_visibility[i-1], self._layer_visibility[i]
            self._selected_layer -= 1

        imgui.same_line()
        if imgui.button("Down") and self._selected_layer < len(self._layers) - 1:
            i = self._selected_layer
            self._layers[i], self._layers[i+1] = self._layers[i+1], self._layers[i]
            self._layer_visibility[i], self._layer_visibility[i+1] = \
                self._layer_visibility[i+1], self._layer_visibility[i]
            self._selected_layer += 1

    def _render_tileset(self) -> None:
        """Render tileset palette for tile selection."""
        # Tileset selection dropdown
        # TODO: Load actual tilesets
        tilesets = ["terrain.png", "objects.png", "decorations.png"]
        if imgui.begin_combo("Tileset", tilesets[0]):
            for tileset in tilesets:
                is_selected = (tileset == tilesets[0])
                if imgui.selectable(tileset, is_selected)[0]:
                    pass  # TODO: Load tileset
            imgui.end_combo()

        # Zoom control
        _, self._tileset_zoom = imgui.slider_float(
            "Zoom", self._tileset_zoom, 1.0, 4.0
        )

        imgui.separator()

        # Tile grid
        # TODO: Render actual tileset texture
        # For now, show a placeholder grid

        tile_size = int(16 * self._tileset_zoom)
        cols = 8
        rows = 8

        # Create a child region for scrolling
        content_height = rows * tile_size + 20
        imgui.begin_child(
            "TilesetGrid",
            imgui.ImVec2(0, min(content_height, 200)),
            imgui.ChildFlags_.borders,
            imgui.WindowFlags_.horizontal_scrollbar
        )

        draw_list = imgui.get_window_draw_list()
        cursor_pos = imgui.get_cursor_screen_pos()

        for row in range(rows):
            for col in range(cols):
                tile_id = row * cols + col

                x = cursor_pos.x + col * tile_size
                y = cursor_pos.y + row * tile_size

                # Tile background
                is_selected = (tile_id == self._selected_tile)

                if is_selected:
                    color = imgui.get_color_u32(imgui.ImVec4(0.4, 0.6, 1.0, 1.0))
                else:
                    # Alternate colors for visibility
                    shade = 0.3 if (row + col) % 2 == 0 else 0.35
                    color = imgui.get_color_u32(imgui.ImVec4(shade, shade, shade, 1.0))

                draw_list.add_rect_filled(
                    imgui.ImVec2(x, y),
                    imgui.ImVec2(x + tile_size - 1, y + tile_size - 1),
                    color
                )

                # Border
                draw_list.add_rect(
                    imgui.ImVec2(x, y),
                    imgui.ImVec2(x + tile_size, y + tile_size),
                    imgui.get_color_u32(imgui.ImVec4(0.5, 0.5, 0.5, 1.0))
                )

        # Handle tile selection
        if imgui.is_window_hovered() and imgui.is_mouse_clicked(imgui.MouseButton_.left):
            mouse_pos = imgui.get_mouse_pos()
            rel_x = mouse_pos.x - cursor_pos.x
            rel_y = mouse_pos.y - cursor_pos.y

            col = int(rel_x // tile_size)
            row = int(rel_y // tile_size)

            if 0 <= col < cols and 0 <= row < rows:
                self._selected_tile = row * cols + col
                self.state.brush_tile = self._selected_tile

        # Reserve space for the grid
        imgui.dummy(imgui.ImVec2(cols * tile_size, rows * tile_size))

        imgui.end_child()

        # Show selected tile info
        imgui.text(f"Selected Tile: {self._selected_tile}")
