"""
Entity Hierarchy Panel.

Displays a tree view of all entities in the world with
create, delete, rename, and selection functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from imgui_bundle import imgui

from editor.panels.base import Panel

if TYPE_CHECKING:
    from engine.core import Game
    from editor.app import EditorState


class EntityHierarchyPanel(Panel):
    """
    Panel for viewing and managing entities in the world.

    Features:
    - Tree view of all entities
    - Click to select
    - Right-click context menu for CRUD operations
    - Search/filter
    - Inline rename
    """

    def __init__(self, game: Game, state: EditorState):
        super().__init__(game, state)

        # Filter
        self._search_filter: str = ""

        # Rename state
        self._renaming_entity_id: int | None = None
        self._rename_buffer: str = ""

        # Delete confirmation
        self._confirm_delete_id: int | None = None

    @property
    def title(self) -> str:
        return "Hierarchy"

    def _render_content(self) -> None:
        """Render the entity hierarchy."""
        world = self.state.current_world

        # Toolbar
        self._render_toolbar()

        imgui.separator()

        # Entity list
        if world is None:
            imgui.text_disabled("No world loaded")
            imgui.text_disabled("Create or load a scene to edit entities")
            return

        # Get and filter entities
        entities = list(world.entities)
        entity_count = len(entities)

        if self._search_filter:
            filter_lower = self._search_filter.lower()
            entities = [
                e for e in entities
                if filter_lower in e.name.lower()
            ]

        # Scrollable list
        if imgui.begin_child(
            "EntityList",
            imgui.ImVec2(0, -1),
            imgui.ChildFlags_.none,
            imgui.WindowFlags_.none
        ):
            for entity in sorted(entities, key=lambda e: e.name):
                self._render_entity_node(entity)

            # Context menu on empty space
            if imgui.begin_popup_context_window("HierarchyContextMenu"):
                if imgui.menu_item("Create Entity")[0]:
                    self._create_entity()
                imgui.end_popup()

        imgui.end_child()

        # Delete confirmation popup
        self._render_delete_confirmation()

        # Status
        if entity_count > 0:
            imgui.text_disabled(f"{entity_count} entities")

    def _render_toolbar(self) -> None:
        """Render the toolbar with search and create button."""
        # Create button
        if imgui.button("+"):
            self._create_entity()

        if imgui.is_item_hovered():
            imgui.set_tooltip("Create new entity")

        imgui.same_line()

        # Search filter
        imgui.set_next_item_width(-1)
        changed, self._search_filter = imgui.input_text_with_hint(
            "##search",
            "Search...",
            self._search_filter
        )

    def _render_entity_node(self, entity) -> None:
        """Render a single entity in the hierarchy."""
        is_selected = self.state.selected_entity_id == entity.id
        is_renaming = self._renaming_entity_id == entity.id

        # Node flags
        flags = (
            imgui.TreeNodeFlags_.leaf |
            imgui.TreeNodeFlags_.no_tree_push_on_open |
            imgui.TreeNodeFlags_.span_avail_width
        )

        if is_selected:
            flags |= imgui.TreeNodeFlags_.selected

        # Inactive entities shown differently
        if not entity.active:
            imgui.push_style_color(imgui.Col_.text, imgui.ImVec4(0.5, 0.5, 0.5, 1.0))

        imgui.push_id(entity.id)

        if is_renaming:
            # Inline rename input
            imgui.set_next_item_width(-1)
            enter_pressed, self._rename_buffer = imgui.input_text(
                "##rename",
                self._rename_buffer,
                imgui.InputTextFlags_.enter_returns_true |
                imgui.InputTextFlags_.auto_select_all
            )

            # Focus the input on first frame
            if imgui.is_item_appearing():
                imgui.set_keyboard_focus_here(-1)

            # Confirm on Enter or focus lost
            if enter_pressed:
                self._confirm_rename(entity)
            elif not imgui.is_item_focused() and not imgui.is_item_appearing():
                self._cancel_rename()

        else:
            # Normal tree node display
            # Add icon based on entity state
            icon = "[*]" if entity.active else "[ ]"
            node_label = f"{icon} {entity.name}"

            if imgui.tree_node_ex(node_label, flags):
                pass  # Leaf node, no children

            # Selection on click
            if imgui.is_item_clicked(imgui.MouseButton_.left):
                self.state.select_entity(entity.id)

            # Double-click to rename
            if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(imgui.MouseButton_.left):
                self._start_rename(entity)

        # Context menu
        if imgui.begin_popup_context_item(f"EntityContext_{entity.id}"):
            if imgui.menu_item("Rename", "F2")[0]:
                self._start_rename(entity)

            if imgui.menu_item("Duplicate", "Ctrl+D")[0]:
                self._duplicate_entity(entity)

            imgui.separator()

            active_label = "Deactivate" if entity.active else "Activate"
            if imgui.menu_item(active_label)[0]:
                entity.active = not entity.active
                self.state.mark_dirty()

            imgui.separator()

            if imgui.menu_item("Delete", "Del")[0]:
                self._confirm_delete_id = entity.id

            imgui.end_popup()

        # Show tags as tooltip
        if imgui.is_item_hovered() and entity.tags:
            imgui.set_tooltip(f"Tags: {', '.join(entity.tags)}")

        imgui.pop_id()

        if not entity.active:
            imgui.pop_style_color()

    def _render_delete_confirmation(self) -> None:
        """Render delete confirmation popup."""
        if self._confirm_delete_id is None:
            return

        entity = self.state.current_world.get_entity(self._confirm_delete_id)
        if entity is None:
            self._confirm_delete_id = None
            return

        imgui.open_popup("Delete Entity?")

        center = imgui.get_main_viewport().get_center()
        imgui.set_next_window_pos(center, imgui.Cond_.appearing, imgui.ImVec2(0.5, 0.5))

        if imgui.begin_popup_modal("Delete Entity?", None, imgui.WindowFlags_.always_auto_resize)[0]:
            imgui.text(f"Delete '{entity.name}'?")
            imgui.text_disabled("This action cannot be undone.")

            imgui.separator()

            if imgui.button("Delete", imgui.ImVec2(120, 0)):
                self._delete_entity(entity)
                imgui.close_current_popup()

            imgui.same_line()

            if imgui.button("Cancel", imgui.ImVec2(120, 0)):
                self._confirm_delete_id = None
                imgui.close_current_popup()

            imgui.end_popup()

    def _create_entity(self) -> None:
        """Create a new entity."""
        if self.state.current_world is None:
            return

        entity = self.state.current_world.create_entity("New Entity")
        self.state.select_entity(entity.id)
        self.state.mark_dirty()

        # Start rename immediately
        self._start_rename(entity)

    def _delete_entity(self, entity) -> None:
        """Delete an entity."""
        if self.state.current_world is None:
            return

        # Clear selection if deleting selected entity
        if self.state.selected_entity_id == entity.id:
            self.state.select_entity(None)

        self.state.current_world.destroy_entity(entity)
        self.state.mark_dirty()
        self._confirm_delete_id = None

    def _duplicate_entity(self, entity) -> None:
        """Duplicate an entity with all its components."""
        if self.state.current_world is None:
            return

        # Create new entity
        new_entity = self.state.current_world.create_entity(f"{entity.name} (Copy)")

        # Copy components
        for component in entity.components:
            new_entity.add(component.clone())

        # Copy tags
        for tag in entity.tags:
            new_entity.add_tag(tag)

        # Copy active state
        new_entity.active = entity.active

        self.state.select_entity(new_entity.id)
        self.state.mark_dirty()

    def _start_rename(self, entity) -> None:
        """Start inline rename for an entity."""
        self._renaming_entity_id = entity.id
        self._rename_buffer = entity.name

    def _confirm_rename(self, entity) -> None:
        """Confirm the rename operation."""
        if self._rename_buffer.strip():
            entity.name = self._rename_buffer.strip()
            self.state.mark_dirty()
        self._cancel_rename()

    def _cancel_rename(self) -> None:
        """Cancel the rename operation."""
        self._renaming_entity_id = None
        self._rename_buffer = ""

    def update(self, dt: float) -> None:
        """Handle keyboard shortcuts."""
        if not self.is_focused:
            return

        # Delete key
        if imgui.is_key_pressed(imgui.Key.delete):
            entity = self.state.get_selected_entity()
            if entity:
                self._confirm_delete_id = entity.id

        # F2 to rename
        if imgui.is_key_pressed(imgui.Key.f2):
            entity = self.state.get_selected_entity()
            if entity and self._renaming_entity_id is None:
                self._start_rename(entity)

        # Escape to cancel rename
        if imgui.is_key_pressed(imgui.Key.escape):
            if self._renaming_entity_id is not None:
                self._cancel_rename()
