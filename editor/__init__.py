"""
Editor module.

Provides the visual development environment for creating games.
"""

from editor.app import EditorScene, EditorState
from editor.imgui_backend import ImGuiRenderer
from editor.panels import (
    Panel,
    PanelManager,
    SceneViewPanel,
    MapEditorPanel,
    AssetBrowserPanel,
    PropertiesPanel,
)

__all__ = [
    "EditorScene",
    "EditorState",
    "ImGuiRenderer",
    "Panel",
    "PanelManager",
    "SceneViewPanel",
    "MapEditorPanel",
    "AssetBrowserPanel",
    "PropertiesPanel",
]
