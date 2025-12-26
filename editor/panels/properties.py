"""
Properties panel - inspect and edit selected objects.

Shows properties of:
- Selected entity
- Selected tile
- Selected layer
- Map properties
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from imgui_bundle import imgui

from editor.panels.base import Panel

if TYPE_CHECKING:
    from engine.core import Game
    from editor.app import EditorState


class PropertiesPanel(Panel):
    """
    Properties inspector panel.

    Shows editable properties for the currently selected object.
    """

    @property
    def title(self) -> str:
        return "Properties"

    def __init__(self, game: Game, state: EditorState):
        super().__init__(game, state)

        # Cached property data
        self._entity_data: dict[str, Any] = {}
        self._tile_data: dict[str, Any] = {}
        self._layer_data: dict[str, Any] = {}

    def _render_content(self) -> None:
        # Determine what to show based on selection
        if self.state.selected_entity_id is not None:
            self._render_entity_properties()
        elif self.state.selected_tile is not None:
            self._render_tile_properties()
        elif self.state.selected_layer is not None:
            self._render_layer_properties()
        else:
            self._render_map_properties()

    def _render_entity_properties(self) -> None:
        """Render properties for a selected entity."""
        imgui.text("Entity Properties")
        imgui.separator()

        entity_id = self.state.selected_entity_id
        imgui.text(f"ID: {entity_id}")

        # Name
        name = self._entity_data.get("name", "Entity")
        changed, new_name = imgui.input_text("Name", name)
        if changed:
            self._entity_data["name"] = new_name
            self.state.mark_dirty()

        imgui.separator()
        imgui.text("Transform")

        # Position
        pos = self._entity_data.get("position", [0.0, 0.0])
        changed, new_pos = imgui.drag_float2("Position", pos, 1.0)
        if changed:
            self._entity_data["position"] = list(new_pos)
            self.state.mark_dirty()

        # Rotation
        rotation = self._entity_data.get("rotation", 0.0)
        changed, new_rot = imgui.drag_float("Rotation", rotation, 1.0, 0.0, 360.0)
        if changed:
            self._entity_data["rotation"] = new_rot
            self.state.mark_dirty()

        # Scale
        scale = self._entity_data.get("scale", [1.0, 1.0])
        changed, new_scale = imgui.drag_float2("Scale", scale, 0.1)
        if changed:
            self._entity_data["scale"] = list(new_scale)
            self.state.mark_dirty()

        imgui.separator()
        imgui.text("Components")

        # List components (mock data)
        components = self._entity_data.get("components", [
            "Transform", "Sprite", "Collider"
        ])

        for i, comp in enumerate(components):
            if imgui.collapsing_header(comp):
                imgui.indent()
                imgui.text(f"Component: {comp}")
                imgui.text("(Properties would go here)")
                imgui.unindent()

        # Add component button
        if imgui.button("Add Component"):
            imgui.open_popup("AddComponentPopup")

        if imgui.begin_popup("AddComponentPopup"):
            available = ["Health", "Velocity", "AI", "Dialog", "Inventory"]
            for comp in available:
                if imgui.selectable(comp)[0]:
                    components.append(comp)
                    self._entity_data["components"] = components
                    self.state.mark_dirty()
            imgui.end_popup()

    def _render_tile_properties(self) -> None:
        """Render properties for a selected tile."""
        imgui.text("Tile Properties")
        imgui.separator()

        tile_x, tile_y = self.state.selected_tile
        imgui.text(f"Position: ({tile_x}, {tile_y})")

        # Tile ID
        tile_id = self._tile_data.get("id", 0)
        changed, new_id = imgui.input_int("Tile ID", tile_id)
        if changed:
            self._tile_data["id"] = max(0, new_id)
            self.state.mark_dirty()

        imgui.separator()
        imgui.text("Collision")

        # Collision type
        collision_types = ["None", "Solid", "Platform", "Trigger", "Water"]
        current = self._tile_data.get("collision", 0)

        if imgui.begin_combo("Type", collision_types[current]):
            for i, coll_type in enumerate(collision_types):
                is_selected = (i == current)
                if imgui.selectable(coll_type, is_selected)[0]:
                    self._tile_data["collision"] = i
                    self.state.mark_dirty()
            imgui.end_combo()

        imgui.separator()
        imgui.text("Properties")

        # Custom properties
        props = self._tile_data.get("properties", {})

        if imgui.button("Add Property"):
            props[f"prop_{len(props)}"] = ""
            self._tile_data["properties"] = props
            self.state.mark_dirty()

        for key in list(props.keys()):
            imgui.push_id(key)

            # Key
            changed, new_key = imgui.input_text("##key", key, 128)

            imgui.same_line()

            # Value
            value = props[key]
            changed_val, new_val = imgui.input_text("##value", str(value))

            imgui.same_line()

            # Delete button
            if imgui.button("X"):
                del props[key]
                self.state.mark_dirty()
            elif changed or changed_val:
                if changed and new_key != key:
                    props[new_key] = props.pop(key)
                if changed_val:
                    props[new_key if changed else key] = new_val
                self.state.mark_dirty()

            imgui.pop_id()

    def _render_layer_properties(self) -> None:
        """Render properties for a selected layer."""
        imgui.text("Layer Properties")
        imgui.separator()

        layer_name = self.state.selected_layer
        imgui.text(f"Layer: {layer_name}")

        # Layer name
        changed, new_name = imgui.input_text("Name", layer_name)
        if changed:
            self.state.selected_layer = new_name
            self.state.mark_dirty()

        imgui.separator()

        # Visibility
        visible = self._layer_data.get("visible", True)
        changed, visible = imgui.checkbox("Visible", visible)
        if changed:
            self._layer_data["visible"] = visible
            self.state.mark_dirty()

        # Opacity
        opacity = self._layer_data.get("opacity", 1.0)
        changed, opacity = imgui.slider_float("Opacity", opacity, 0.0, 1.0)
        if changed:
            self._layer_data["opacity"] = opacity
            self.state.mark_dirty()

        imgui.separator()
        imgui.text("Parallax")

        # Parallax
        parallax = self._layer_data.get("parallax", [1.0, 1.0])
        changed, new_parallax = imgui.drag_float2("Factor", parallax, 0.1)
        if changed:
            self._layer_data["parallax"] = list(new_parallax)
            self.state.mark_dirty()

        # Offset
        offset = self._layer_data.get("offset", [0.0, 0.0])
        changed, new_offset = imgui.drag_float2("Offset", offset, 1.0)
        if changed:
            self._layer_data["offset"] = list(new_offset)
            self.state.mark_dirty()

    def _render_map_properties(self) -> None:
        """Render properties for the current map."""
        imgui.text("Map Properties")
        imgui.separator()

        # Map name
        map_name = "Untitled Map"
        changed, new_name = imgui.input_text("Name", map_name)

        imgui.separator()
        imgui.text("Dimensions")

        # Size
        size = [80, 45]
        changed, new_size = imgui.input_int2("Size (tiles)", size)

        tile_size = 16
        changed, new_tile = imgui.input_int("Tile Size", tile_size)

        imgui.text(f"Pixels: {size[0] * tile_size} x {size[1] * tile_size}")

        imgui.separator()
        imgui.text("Background")

        # Background color
        bg_color = [0.1, 0.1, 0.15, 1.0]
        changed, new_color = imgui.color_edit4("Color", bg_color)

        imgui.separator()
        imgui.text("Custom Properties")

        # Add property button
        if imgui.button("Add Property"):
            pass

        # Property list would go here
        imgui.text("(No custom properties)")
