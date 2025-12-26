"""
Editor panels module.

Provides dockable panels for the editor interface.
"""

from editor.panels.base import Panel, PanelManager
from editor.panels.scene_view import SceneViewPanel
from editor.panels.map_editor import MapEditorPanel
from editor.panels.asset_browser import AssetBrowserPanel
from editor.panels.properties import PropertiesPanel

__all__ = [
    "Panel",
    "PanelManager",
    "SceneViewPanel",
    "MapEditorPanel",
    "AssetBrowserPanel",
    "PropertiesPanel",
]
