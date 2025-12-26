"""
Editor panels module.

Provides dockable panels for the editor interface.
"""

from editor.panels.base import Panel, PanelManager
from editor.panels.scene_view import SceneViewPanel
from editor.panels.map_editor import MapEditorPanel
from editor.panels.asset_browser import AssetBrowserPanel
from editor.panels.properties import PropertiesPanel
from editor.panels.entity_hierarchy import EntityHierarchyPanel
from editor.panels.component_inspector import ComponentInspectorPanel

__all__ = [
    "Panel",
    "PanelManager",
    "SceneViewPanel",
    "MapEditorPanel",
    "AssetBrowserPanel",
    "PropertiesPanel",
    "EntityHierarchyPanel",
    "ComponentInspectorPanel",
]
