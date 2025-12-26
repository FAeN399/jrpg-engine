# Directory Log: editor/
**Date:** 2025-12-25
**Logger:** AI Log Man Robot

---

## Overview

The `editor/` directory contains a visual development environment built with ImGui (via imgui-bundle), integrated with Pygame and ModernGL for GPU-accelerated rendering.

**Total Files:** 11 Python files
**Dependency:** Requires `imgui-bundle` (may not be installed in all environments)

---

## File Structure

```
editor/
  __init__.py          # Public API exports
  app.py               # Main editor application (451 lines)
  imgui_backend.py     # ModernGL ImGui renderer (313 lines)
  panels/
    __init__.py        # Panel exports
    base.py            # Panel base classes (159 lines)
    scene_view.py      # Main viewport (262 lines)
    map_editor.py      # Tile editing tools (271 lines)
    asset_browser.py   # File browser (399 lines)
    properties.py      # Property inspector (273 lines)
  utils/
    __init__.py        # Empty (placeholder)
  widgets/
    __init__.py        # Empty (placeholder)
```

---

## Component Analysis

### 1. app.py - EditorScene
**Purpose:** Main editor scene integrating all panels and handling global operations.

**Key Classes:**
- `EditorMode` - Enum: EDIT, PLAY, PAUSED
- `EditorConfig` - Configuration dataclass
- `EditorState` - Global selection/tool state
- `EditorScene` - Main Scene subclass

**Features:**
- ImGui dockspace with full window coverage
- Main menu bar (File, Edit, View, Project, Help)
- Status bar with mode/FPS/selection info
- Keyboard shortcuts (Ctrl+S save, Ctrl+Z undo, etc.)
- Dark theme styling

**TODOs Noted in Code:**
- Line 153: "TODO: Show quit confirmation if dirty"
- Line 397: "TODO: File dialog" (open project)
- Line 411: "TODO: File dialog" (save as)

---

### 2. imgui_backend.py - ImGuiRenderer
**Purpose:** Custom ImGui renderer for ModernGL context.

**Features:**
- GLSL 330 shaders for ImGui rendering
- Pygame event -> ImGui input translation
- Font atlas texture management
- Dynamic buffer resizing for draw data
- Keyboard/mouse mapping

**Technical Details:**
- Scissor testing for clipping
- Proper blend mode setup
- 32-bit index buffers (large UI support)

---

### 3. panels/base.py - Panel & PanelManager
**Purpose:** Base infrastructure for dockable panels.

**Panel Base Class:**
- Abstract `title` property
- `visible` state
- `_focused` tracking
- `update(dt)` and `render()` lifecycle

**PanelManager:**
- Panel registry with ID lookup
- Type-based panel retrieval
- Show/hide/toggle operations

---

### 4. panels/scene_view.py - SceneViewPanel
**Purpose:** Main game world viewport for editing.

**Features:**
- Off-screen framebuffer rendering to texture
- Camera panning (middle mouse drag)
- Zoom with mouse wheel (towards cursor)
- Screen-to-world coordinate conversion
- Tile position tracking
- Overlay with camera/zoom info

**Technical Details:**
- Uses `moderngl.Framebuffer` for viewport
- Proper texture cleanup on resize
- Zoom clamped to 0.25x - 4.0x

**TODOs:**
- Line 129: "TODO: Render tilemap"
- Line 130: "TODO: Render entities"
- Line 131: "TODO: Render selection"
- Line 139: "TODO: Use shader for better performance" (grid)
- Line 244: "TODO: Actually paint the tile"

---

### 5. panels/map_editor.py - MapEditorPanel
**Purpose:** Tile editing tools and layer management.

**Features:**
- Tool palette: Select, Brush, Fill, Rectangle, Eraser, Eyedropper
- Brush size slider (1-10)
- Layer list with visibility toggles
- Layer reordering (up/down)
- Tileset palette grid view
- Tile selection by click

**TODOs:**
- Line 185: "TODO: Load actual tilesets"
- Line 191: "TODO: Load tileset"
- Line 202: "TODO: Render actual tileset texture"

---

### 6. panels/asset_browser.py - AssetBrowserPanel
**Purpose:** Project file browser with tree navigation.

**Features:**
- Folder tree (left column)
- File grid/list view (right column)
- Asset type detection by extension
- Filter text input
- Grid/list view toggle
- File size tracking

**Asset Types Recognized:**
- Images: .png, .jpg, .jpeg, .gif, .bmp
- Audio: .wav, .mp3, .ogg, .flac
- Data: .json, .yaml, .yml
- Scripts: .py
- Maps: .tmx, .tmj

**TODOs:**
- Line 113: "TODO: Hot reload detection"
- Line 397: "TODO: Open in appropriate editor"

---

### 7. panels/properties.py - PropertiesPanel
**Purpose:** Inspector for selected entities/tiles/layers.

**Modes:**
- Entity properties (position, rotation, scale, components)
- Tile properties (ID, collision type, custom props)
- Layer properties (visible, opacity, parallax)
- Map properties (name, dimensions, background)

**Features:**
- Component listing with collapsible headers
- "Add Component" popup
- Custom key-value property editor
- Collision type dropdown

---

## Potential Issues

### 1. Empty utils/ and widgets/ directories
The `editor/utils/` and `editor/widgets/` directories only contain empty `__init__.py` files. These appear to be placeholders for future development.

### 2. Hardcoded asset path
`AssetBrowserPanel._root_path = Path("game/assets")` - hardcoded, not configurable.

### 3. Missing file dialogs
Project open/save operations print TODO messages and don't actually show file dialogs.

### 4. No actual tilemap rendering
SceneViewPanel._render_scene() clears the FBO but doesn't render any actual content.

### 5. Properties panel uses mock data
Entity properties panel shows cached data, not connected to actual entities.

---

## Architecture Notes

- Clean separation: Each panel is self-contained
- State shared via `EditorState` singleton pattern
- Panels update independently each frame
- ImGui handles layout/docking automatically
- Uses ModernGL FBO for off-screen scene rendering

---

## Dependencies

```python
from imgui_bundle import imgui, immapp
from imgui_bundle.python_backends import compute_fb_scale
```

If `imgui-bundle` is not installed, the entire editor module will fail to import.

---

*End of editor/ log*
