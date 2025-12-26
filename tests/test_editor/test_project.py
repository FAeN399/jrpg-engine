"""
Test project save/load functionality.
"""

import tempfile
import os
from pathlib import Path

import pytest


def test_project_data_serialization():
    """Test ProjectData to_dict/from_dict."""
    # Import here to avoid editor package init
    import sys
    # Ensure framework components are registered
    import framework.components  # noqa: F401

    from editor.project import ProjectData

    project = ProjectData(
        name="TestProject",
        grid_size=32,
        show_grid=True,
        show_collision=False,
    )

    # Serialize
    data = project.to_dict()
    assert data["name"] == "TestProject"
    assert data["grid_size"] == 32

    # Deserialize
    loaded = ProjectData.from_dict(data)
    assert loaded.name == "TestProject"
    assert loaded.grid_size == 32


def test_tilemap_serialization():
    """Test tilemap to_dict/from_dict."""
    from engine.graphics.tilemap import Tilemap
    from editor.project import tilemap_to_dict, tilemap_from_dict

    # Create tilemap
    tilemap = Tilemap(16, 16, 16)
    tilemap.add_layer("Ground")
    tilemap.add_layer("Objects")

    ground = tilemap.get_layer("Ground")
    ground.set_tile(0, 0, 1)
    ground.set_tile(1, 0, 2)
    ground.set_tile(0, 1, 3)

    # Serialize
    data = tilemap_to_dict(tilemap)
    assert len(data["layers"]) == 2

    # Deserialize
    loaded = tilemap_from_dict(data)
    assert len(loaded.layers) == 2

    loaded_ground = loaded.get_layer("Ground")
    assert loaded_ground.get_tile(0, 0) == 1
    assert loaded_ground.get_tile(1, 0) == 2
    assert loaded_ground.get_tile(0, 1) == 3


def test_world_serialization():
    """Test world to_dict/from_dict."""
    from engine.core.world import World
    from framework.components import Transform, Health, CharacterStats
    from editor.project import world_to_dict, world_from_dict

    # Create world with entities
    world = World()

    player = world.create_entity("Player")
    player.add(Transform(x=100, y=200))
    player.add(Health(current=80, max_hp=100))
    player.add(CharacterStats(level=5, strength=12))
    player.add_tag("player")
    player.add_tag("party")

    enemy = world.create_entity("Goblin")
    enemy.add(Transform(x=300, y=200))
    enemy.add(Health(current=30, max_hp=30))
    enemy.add_tag("enemy")

    # Serialize
    data = world_to_dict(world)
    assert len(data) == 2

    # Deserialize
    loaded_world = World()
    world_from_dict(loaded_world, data)

    loaded_player = loaded_world.get_entity_by_name("Player")
    assert loaded_player is not None
    assert loaded_player.has(Transform)
    assert loaded_player.has(Health)
    assert loaded_player.has(CharacterStats)

    t = loaded_player.get(Transform)
    assert t.x == 100 and t.y == 200

    h = loaded_player.get(Health)
    assert h.current == 80 and h.max_hp == 100

    s = loaded_player.get(CharacterStats)
    assert s.level == 5 and s.strength == 12

    assert loaded_player.has_tag("player")
    assert loaded_player.has_tag("party")


def test_save_load_roundtrip():
    """Test full project save/load round-trip."""
    import json
    from engine.graphics.tilemap import Tilemap
    from engine.core.world import World
    from framework.components import Transform, Health
    from editor.project import (
        ProjectData, tilemap_to_dict, tilemap_from_dict,
        world_to_dict, world_from_dict,
    )

    # Build project
    project = ProjectData(
        name="RoundtripTest",
        grid_size=16,
    )

    # Add tilemap
    tilemap = Tilemap(8, 8, 16)
    tilemap.add_layer("Ground")
    tilemap.get_layer("Ground").set_tile(0, 0, 5)
    project.tilemap = tilemap_to_dict(tilemap)

    # Add entities
    world = World()
    entity = world.create_entity("TestEntity")
    entity.add(Transform(x=50, y=100))
    entity.add(Health(current=10, max_hp=20))
    project.entities = world_to_dict(world)

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=".jrpg", delete=False) as f:
        temp_path = Path(f.name)

    try:
        # Save directly (bypassing tkinter dialogs)
        data = project.to_dict()
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        # Load directly
        with open(temp_path, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        loaded = ProjectData.from_dict(loaded_data)
        assert loaded is not None
        assert loaded.name == "RoundtripTest"
        assert loaded.grid_size == 16

        # Verify tilemap
        loaded_tilemap = tilemap_from_dict(loaded.tilemap)
        assert loaded_tilemap.get_layer("Ground").get_tile(0, 0) == 5

        # Verify entities
        loaded_world = World()
        world_from_dict(loaded_world, loaded.entities)
        loaded_entity = loaded_world.get_entity_by_name("TestEntity")
        assert loaded_entity is not None
        assert loaded_entity.get(Transform).x == 50
        assert loaded_entity.get(Health).current == 10

    finally:
        os.unlink(temp_path)
