"""
Project file management for the JRPG Editor.

Handles saving and loading projects using tkinter file dialogs.
Projects are serialized as JSON files containing:
- Project metadata
- Tilemap data
- Entity data (World state)
- Editor settings
"""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import TYPE_CHECKING, Any
from dataclasses import dataclass, field
import threading

import numpy as np

if TYPE_CHECKING:
    from editor.app import EditorState
    from engine.core.world import World
    from engine.graphics.tilemap import Tilemap


# File type definitions
PROJECT_FILETYPES = [
    ("JRPG Project", "*.jrpg"),
    ("JSON files", "*.json"),
    ("All files", "*.*"),
]

TILEMAP_FILETYPES = [
    ("Tilemap", "*.tilemap"),
    ("JSON files", "*.json"),
    ("All files", "*.*"),
]


def _get_tk_root() -> tk.Tk:
    """Get or create a hidden Tk root window for dialogs."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.attributes('-topmost', True)  # Keep dialog on top
    return root


def ask_open_file(
    title: str = "Open File",
    filetypes: list[tuple[str, str]] | None = None,
    initial_dir: str | Path | None = None,
) -> Path | None:
    """
    Show an open file dialog.

    Args:
        title: Dialog window title
        filetypes: List of (description, pattern) tuples
        initial_dir: Starting directory

    Returns:
        Selected file path, or None if cancelled
    """
    root = _get_tk_root()
    try:
        filetypes = filetypes or PROJECT_FILETYPES
        initial_dir = str(initial_dir) if initial_dir else None

        filepath = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes,
            initialdir=initial_dir,
        )

        if filepath:
            return Path(filepath)
        return None
    finally:
        root.destroy()


def ask_save_file(
    title: str = "Save File",
    filetypes: list[tuple[str, str]] | None = None,
    initial_dir: str | Path | None = None,
    default_extension: str = ".jrpg",
    initial_file: str = "",
) -> Path | None:
    """
    Show a save file dialog.

    Args:
        title: Dialog window title
        filetypes: List of (description, pattern) tuples
        initial_dir: Starting directory
        default_extension: Default file extension
        initial_file: Default filename

    Returns:
        Selected file path, or None if cancelled
    """
    root = _get_tk_root()
    try:
        filetypes = filetypes or PROJECT_FILETYPES
        initial_dir = str(initial_dir) if initial_dir else None

        filepath = filedialog.asksaveasfilename(
            title=title,
            filetypes=filetypes,
            initialdir=initial_dir,
            defaultextension=default_extension,
            initialfile=initial_file,
        )

        if filepath:
            return Path(filepath)
        return None
    finally:
        root.destroy()


def ask_directory(
    title: str = "Select Directory",
    initial_dir: str | Path | None = None,
) -> Path | None:
    """
    Show a directory selection dialog.

    Args:
        title: Dialog window title
        initial_dir: Starting directory

    Returns:
        Selected directory path, or None if cancelled
    """
    root = _get_tk_root()
    try:
        initial_dir = str(initial_dir) if initial_dir else None

        dirpath = filedialog.askdirectory(
            title=title,
            initialdir=initial_dir,
        )

        if dirpath:
            return Path(dirpath)
        return None
    finally:
        root.destroy()


def ask_yes_no(title: str, message: str) -> bool:
    """
    Show a yes/no confirmation dialog.

    Args:
        title: Dialog window title
        message: Message to display

    Returns:
        True if user clicked Yes, False otherwise
    """
    root = _get_tk_root()
    try:
        return messagebox.askyesno(title, message)
    finally:
        root.destroy()


def ask_yes_no_cancel(title: str, message: str) -> bool | None:
    """
    Show a yes/no/cancel confirmation dialog.

    Args:
        title: Dialog window title
        message: Message to display

    Returns:
        True for Yes, False for No, None for Cancel
    """
    root = _get_tk_root()
    try:
        result = messagebox.askyesnocancel(title, message)
        return result
    finally:
        root.destroy()


def show_error(title: str, message: str) -> None:
    """Show an error message dialog."""
    root = _get_tk_root()
    try:
        messagebox.showerror(title, message)
    finally:
        root.destroy()


def show_info(title: str, message: str) -> None:
    """Show an info message dialog."""
    root = _get_tk_root()
    try:
        messagebox.showinfo(title, message)
    finally:
        root.destroy()


# -----------------------------------------------------------------------------
# Project Serialization
# -----------------------------------------------------------------------------

@dataclass
class ProjectData:
    """
    Serializable project data structure.

    Contains all data needed to save/load a complete project.
    """
    version: str = "1.0"
    name: str = "Untitled"

    # Editor settings
    grid_size: int = 16
    show_grid: bool = True
    show_collision: bool = False

    # Tilemap data (if any)
    tilemap: dict | None = None

    # Entity data
    entities: list[dict] = field(default_factory=list)

    # Project-specific properties
    properties: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "name": self.name,
            "grid_size": self.grid_size,
            "show_grid": self.show_grid,
            "show_collision": self.show_collision,
            "tilemap": self.tilemap,
            "entities": self.entities,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ProjectData:
        """Create from dictionary."""
        return cls(
            version=data.get("version", "1.0"),
            name=data.get("name", "Untitled"),
            grid_size=data.get("grid_size", 16),
            show_grid=data.get("show_grid", True),
            show_collision=data.get("show_collision", False),
            tilemap=data.get("tilemap"),
            entities=data.get("entities", []),
            properties=data.get("properties", {}),
        )


def tilemap_to_dict(tilemap) -> dict:
    """
    Serialize a Tilemap to a dictionary.

    Args:
        tilemap: Tilemap instance

    Returns:
        Dictionary representation
    """
    from engine.graphics.tilemap import Tilemap, TileLayer

    layers_data = []
    for layer in tilemap.layers:
        layer_dict = {
            "name": layer.name,
            "width": layer.width,
            "height": layer.height,
            "tiles": layer.tiles.tolist(),  # Convert numpy array to list
            "visible": layer.visible,
            "opacity": layer.opacity,
            "offset_x": layer.offset_x,
            "offset_y": layer.offset_y,
            "parallax_x": layer.parallax_x,
            "parallax_y": layer.parallax_y,
        }
        layers_data.append(layer_dict)

    collision_data = None
    if tilemap.collision:
        collision_data = {
            "width": tilemap.collision.width,
            "height": tilemap.collision.height,
            "data": tilemap.collision.data.tolist(),
        }

    return {
        "width": tilemap.width,
        "height": tilemap.height,
        "tile_size": tilemap.tile_size,
        "layers": layers_data,
        "collision": collision_data,
        "properties": tilemap.properties,
    }


def tilemap_from_dict(data: dict):
    """
    Deserialize a Tilemap from a dictionary.

    Args:
        data: Dictionary representation

    Returns:
        Tilemap instance
    """
    from engine.graphics.tilemap import Tilemap, TileLayer, CollisionLayer

    tilemap = Tilemap(
        width=data["width"],
        height=data["height"],
        tile_size=data.get("tile_size", 16),
    )

    # Load layers
    for layer_data in data.get("layers", []):
        tiles = np.array(layer_data["tiles"], dtype=np.int32)
        layer = TileLayer(
            name=layer_data["name"],
            width=layer_data["width"],
            height=layer_data["height"],
            tiles=tiles,
            visible=layer_data.get("visible", True),
            opacity=layer_data.get("opacity", 1.0),
            offset_x=layer_data.get("offset_x", 0.0),
            offset_y=layer_data.get("offset_y", 0.0),
            parallax_x=layer_data.get("parallax_x", 1.0),
            parallax_y=layer_data.get("parallax_y", 1.0),
        )
        tilemap.layers.append(layer)

    # Load collision
    collision_data = data.get("collision")
    if collision_data:
        coll_array = np.array(collision_data["data"], dtype=bool)
        tilemap.collision = CollisionLayer(
            width=collision_data["width"],
            height=collision_data["height"],
            data=coll_array,
        )

    # Load properties
    tilemap.properties = data.get("properties", {})

    return tilemap


def world_to_dict(world) -> list[dict]:
    """
    Serialize World entities to a list of dictionaries.

    Args:
        world: World instance

    Returns:
        List of entity dictionaries
    """
    entities = []
    for entity in world.entities:
        entities.append(entity.to_dict())
    return entities


def world_from_dict(world, entities_data: list[dict]) -> None:
    """
    Load entities into a World from serialized data.

    Args:
        world: World instance to populate
        entities_data: List of entity dictionaries
    """
    from engine.core.entity import Entity
    from engine.core.component import get_component_type

    # Import framework components to ensure they're registered
    try:
        import framework.components  # noqa: F401
    except ImportError:
        pass  # Framework not available

    for entity_data in entities_data:
        # Create entity
        entity = world.create_entity(entity_data.get("name", ""))
        entity._active = entity_data.get("active", True)

        # Add tags
        for tag in entity_data.get("tags", []):
            entity.add_tag(tag)

        # Add components
        for comp_name, comp_data in entity_data.get("components", {}).items():
            comp_type = get_component_type(comp_name)
            if comp_type:
                try:
                    component = comp_type.model_validate(comp_data)
                    entity.add(component)
                except Exception as e:
                    print(f"Warning: Failed to load component {comp_name}: {e}")
            else:
                print(f"Warning: Unknown component type: {comp_name}")


def save_project(path: Path, project_data: ProjectData) -> bool:
    """
    Save project to a file.

    Args:
        path: File path to save to
        project_data: Project data to save

    Returns:
        True if successful, False otherwise
    """
    try:
        data = project_data.to_dict()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        show_error("Save Error", f"Failed to save project:\n{e}")
        return False


def load_project(path: Path) -> ProjectData | None:
    """
    Load project from a file.

    Args:
        path: File path to load from

    Returns:
        ProjectData if successful, None otherwise
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return ProjectData.from_dict(data)
    except Exception as e:
        show_error("Load Error", f"Failed to load project:\n{e}")
        return None
