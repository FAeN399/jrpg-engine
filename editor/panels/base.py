"""
Base classes for editor panels.

Panels are dockable windows that provide specific functionality
(map editing, asset browsing, properties, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from imgui_bundle import imgui

if TYPE_CHECKING:
    from engine.core import Game
    from editor.app import EditorState


class Panel(ABC):
    """
    Base class for editor panels.

    Panels are dockable ImGui windows that can be shown/hidden
    and provide specific editing functionality.
    """

    def __init__(self, game: Game, state: EditorState):
        self.game = game
        self.state = state
        self.visible = True
        self._focused = False

    @property
    @abstractmethod
    def title(self) -> str:
        """Panel window title."""
        pass

    @property
    def id(self) -> str:
        """Unique panel ID."""
        return f"###{self.__class__.__name__}"

    @property
    def is_focused(self) -> bool:
        """Whether this panel has focus."""
        return self._focused

    def update(self, dt: float) -> None:
        """
        Update panel logic.

        Called each frame regardless of visibility.
        Override for panel-specific updates.
        """
        pass

    def render(self) -> None:
        """Render the panel."""
        if not self.visible:
            return

        # Begin window
        window_flags = self._get_window_flags()

        # Check if window is open
        expanded, opened = imgui.begin(f"{self.title}{self.id}", True, window_flags)
        self.visible = opened

        if expanded:
            self._focused = imgui.is_window_focused()
            self._render_content()

        imgui.end()

    def _get_window_flags(self) -> int:
        """Get ImGui window flags for this panel."""
        return imgui.WindowFlags_.none

    @abstractmethod
    def _render_content(self) -> None:
        """Render the panel content. Override in subclasses."""
        pass

    def on_show(self) -> None:
        """Called when panel becomes visible."""
        pass

    def on_hide(self) -> None:
        """Called when panel is hidden."""
        pass


class PanelManager:
    """
    Manages a collection of editor panels.
    """

    def __init__(self, state: EditorState):
        self.state = state
        self.panels: list[Panel] = []
        self._panels_by_id: dict[str, Panel] = {}

    def add_panel(self, panel: Panel) -> None:
        """Add a panel to the manager."""
        self.panels.append(panel)
        self._panels_by_id[panel.id] = panel

    def remove_panel(self, panel: Panel) -> None:
        """Remove a panel from the manager."""
        if panel in self.panels:
            self.panels.remove(panel)
            del self._panels_by_id[panel.id]

    def get_panel(self, panel_id: str) -> Panel | None:
        """Get a panel by ID."""
        return self._panels_by_id.get(panel_id)

    def get_panel_by_type(self, panel_type: type) -> Panel | None:
        """Get a panel by type."""
        for panel in self.panels:
            if isinstance(panel, panel_type):
                return panel
        return None

    def update(self, dt: float) -> None:
        """Update all panels."""
        for panel in self.panels:
            panel.update(dt)

    def render(self) -> None:
        """Render all visible panels."""
        for panel in self.panels:
            panel.render()

    def show_panel(self, panel_id: str) -> None:
        """Show a panel by ID."""
        panel = self.get_panel(panel_id)
        if panel and not panel.visible:
            panel.visible = True
            panel.on_show()

    def hide_panel(self, panel_id: str) -> None:
        """Hide a panel by ID."""
        panel = self.get_panel(panel_id)
        if panel and panel.visible:
            panel.visible = False
            panel.on_hide()

    def toggle_panel(self, panel_id: str) -> None:
        """Toggle panel visibility."""
        panel = self.get_panel(panel_id)
        if panel:
            if panel.visible:
                self.hide_panel(panel_id)
            else:
                self.show_panel(panel_id)
