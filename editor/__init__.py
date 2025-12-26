"""
Editor module.

Provides the visual development environment for creating games.

Note: The visual editor components require imgui_bundle to be installed.
Project serialization (editor.project) works without imgui_bundle.
"""

# Core utilities that don't require imgui
from editor.project import (
    ProjectData,
    ask_open_file,
    ask_save_file,
    ask_directory,
    ask_yes_no,
    save_project,
    load_project,
    tilemap_to_dict,
    tilemap_from_dict,
    world_to_dict,
    world_from_dict,
)

__all__ = [
    # Project utilities (always available)
    "ProjectData",
    "ask_open_file",
    "ask_save_file",
    "ask_directory",
    "ask_yes_no",
    "save_project",
    "load_project",
    "tilemap_to_dict",
    "tilemap_from_dict",
    "world_to_dict",
    "world_from_dict",
]

# ImGui-dependent components (optional)
try:
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

    __all__.extend([
        "EditorScene",
        "EditorState",
        "ImGuiRenderer",
        "Panel",
        "PanelManager",
        "SceneViewPanel",
        "MapEditorPanel",
        "AssetBrowserPanel",
        "PropertiesPanel",
    ])
except ImportError:
    # imgui_bundle not installed - editor UI not available
    pass
