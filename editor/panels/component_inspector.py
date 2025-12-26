"""
Component Inspector Panel.

Displays and edits all components on the selected entity
using dynamic Pydantic field reflection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from imgui_bundle import imgui

from editor.panels.base import Panel
from editor.widgets.field_editors import render_field
from engine.core.component import get_all_component_types

if TYPE_CHECKING:
    from engine.core import Game
    from engine.core.entity import Entity
    from engine.core.component import Component
    from editor.app import EditorState


class ComponentInspectorPanel(Panel):
    """
    Panel for inspecting and editing entity components.

    Features:
    - Entity info header (ID, name, active)
    - Tag management
    - Component list with collapsible sections
    - Dynamic field editing based on Pydantic types
    - Add/remove components
    """

    def __init__(self, game: Game, state: EditorState):
        super().__init__(game, state)

        # Add component popup state
        self._component_search: str = ""
        self._show_add_popup: bool = False

        # Tag input
        self._new_tag: str = ""

    @property
    def title(self) -> str:
        return "Inspector"

    def _render_content(self) -> None:
        """Render the inspector content."""
        entity = self.state.get_selected_entity()

        if entity is None:
            self._render_no_selection()
            return

        # Entity header
        self._render_entity_header(entity)

        imgui.separator()

        # Tags section
        self._render_tags_section(entity)

        imgui.separator()

        # Components section
        self._render_components_section(entity)

        # Add component button
        imgui.separator()
        self._render_add_component_button(entity)

    def _render_no_selection(self) -> None:
        """Render placeholder when nothing is selected."""
        imgui.text_disabled("No entity selected")
        imgui.spacing()
        imgui.text_disabled("Select an entity in the Hierarchy")
        imgui.text_disabled("to view and edit its properties.")

    def _render_entity_header(self, entity: Entity) -> None:
        """Render entity info header."""
        # Entity ID (read-only)
        imgui.text_disabled(f"ID: {entity.id}")

        # Entity name (editable)
        imgui.set_next_item_width(-1)
        changed, new_name = imgui.input_text("##name", entity.name)
        if changed and new_name.strip():
            entity.name = new_name.strip()
            self.state.mark_dirty()

        # Active toggle
        changed, active = imgui.checkbox("Active", entity.active)
        if changed:
            entity.active = active
            self.state.mark_dirty()

    def _render_tags_section(self, entity: Entity) -> None:
        """Render tags section."""
        if imgui.collapsing_header("Tags", imgui.TreeNodeFlags_.default_open)[0]:
            imgui.indent()

            # Show existing tags
            tags = list(entity.tags)
            tags_to_remove = []

            for tag in tags:
                imgui.push_id(tag)

                # Remove button
                if imgui.small_button("x"):
                    tags_to_remove.append(tag)

                imgui.same_line()
                imgui.text(tag)

                imgui.pop_id()

            # Remove tags
            for tag in tags_to_remove:
                entity.remove_tag(tag)
                self.state.mark_dirty()

            # Add new tag
            imgui.set_next_item_width(imgui.get_content_region_avail().x - 50)
            enter_pressed, self._new_tag = imgui.input_text(
                "##newtag",
                self._new_tag,
                imgui.InputTextFlags_.enter_returns_true
            )

            imgui.same_line()

            if imgui.button("Add") or enter_pressed:
                if self._new_tag.strip():
                    entity.add_tag(self._new_tag.strip())
                    self.state.mark_dirty()
                    self._new_tag = ""

            imgui.unindent()

    def _render_components_section(self, entity: Entity) -> None:
        """Render all components on the entity."""
        components = list(entity.components)

        if not components:
            imgui.text_disabled("No components")
            return

        for component in components:
            self._render_component(entity, component)

    def _render_component(self, entity: Entity, component: Component) -> None:
        """Render a single component with all its fields."""
        comp_type = type(component)
        comp_name = comp_type.__name__

        # Collapsible header
        flags = imgui.TreeNodeFlags_.default_open | imgui.TreeNodeFlags_.framed

        header_open = imgui.collapsing_header(comp_name, flags)[0]

        # Context menu
        if imgui.begin_popup_context_item(f"ComponentMenu_{comp_name}"):
            if imgui.menu_item("Reset to Defaults")[0]:
                self._reset_component(entity, comp_type)

            imgui.separator()

            if imgui.menu_item("Remove Component")[0]:
                entity.remove(comp_type)
                self.state.mark_dirty()

            imgui.end_popup()

        if header_open:
            imgui.indent()

            # Render all fields
            for field_name, field_info in component.model_fields.items():
                # Skip private fields
                if field_name.startswith('_'):
                    continue

                field_value = getattr(component, field_name)
                field_type = field_info.annotation

                imgui.push_id(field_name)

                # Render the field
                changed, new_value = render_field(
                    field_name,
                    field_value,
                    field_type,
                    field_info
                )

                if changed:
                    try:
                        setattr(component, field_name, new_value)
                        self.state.mark_dirty()
                    except Exception as e:
                        # Validation error - show tooltip
                        if imgui.is_item_hovered():
                            imgui.set_tooltip(f"Invalid: {e}")

                imgui.pop_id()

            imgui.unindent()

    def _render_add_component_button(self, entity: Entity) -> None:
        """Render the add component button and popup."""
        button_width = imgui.get_content_region_avail().x

        if imgui.button("Add Component", imgui.ImVec2(button_width, 0)):
            imgui.open_popup("AddComponentPopup")
            self._component_search = ""

        self._render_add_component_popup(entity)

    def _render_add_component_popup(self, entity: Entity) -> None:
        """Render the add component popup."""
        if not imgui.begin_popup("AddComponentPopup"):
            return

        # Search filter
        imgui.set_next_item_width(-1)
        _, self._component_search = imgui.input_text_with_hint(
            "##search",
            "Search components...",
            self._component_search
        )

        imgui.separator()

        # Get all registered component types
        all_types = get_all_component_types()

        # Filter out already-attached components
        existing_types = {type(c).__name__ for c in entity.components}

        # Filter by search
        search_lower = self._component_search.lower()

        available = [
            (name, cls) for name, cls in all_types.items()
            if name not in existing_types and search_lower in name.lower()
        ]

        if not available:
            if self._component_search:
                imgui.text_disabled("No matching components")
            else:
                imgui.text_disabled("All components attached")
        else:
            # Scrollable list
            if imgui.begin_child(
                "ComponentList",
                imgui.ImVec2(250, 200),
                imgui.ChildFlags_.border
            ):
                for name, cls in sorted(available, key=lambda x: x[0]):
                    if imgui.selectable(name)[0]:
                        try:
                            # Create default instance and add
                            entity.add(cls())
                            self.state.mark_dirty()
                            imgui.close_current_popup()
                        except Exception as e:
                            print(f"Failed to add {name}: {e}")

                    # Show docstring as tooltip
                    if imgui.is_item_hovered() and cls.__doc__:
                        imgui.set_tooltip(cls.__doc__.strip()[:200])

            imgui.end_child()

        imgui.end_popup()

    def _reset_component(self, entity: Entity, comp_type: type) -> None:
        """Reset a component to its default values."""
        # Remove and re-add with defaults
        entity.remove(comp_type)
        entity.add(comp_type())
        self.state.mark_dirty()
