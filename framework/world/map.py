"""
Map system - loading, collision, transitions.

Supports Tiled JSON format (.tmj) for map data.
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Any
from enum import Enum, auto

if TYPE_CHECKING:
    from engine.core import Game


class TileProperty(Enum):
    """Special tile properties."""
    SOLID = auto()
    WATER = auto()
    PIT = auto()
    DAMAGE = auto()
    SLOW = auto()
    ICE = auto()


@dataclass
class MapTile:
    """A single tile in the map."""
    gid: int = 0  # Global tile ID
    flip_h: bool = False
    flip_v: bool = False
    flip_d: bool = False  # Diagonal flip


@dataclass
class MapLayer:
    """A layer of tiles or objects."""
    name: str = ""
    layer_type: str = "tilelayer"  # tilelayer, objectgroup, imagelayer
    visible: bool = True
    opacity: float = 1.0
    offset_x: float = 0.0
    offset_y: float = 0.0
    parallax_x: float = 1.0
    parallax_y: float = 1.0
    tiles: list[list[MapTile]] = field(default_factory=list)
    objects: list[dict[str, Any]] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class MapTileset:
    """Reference to a tileset used in the map."""
    name: str = ""
    first_gid: int = 1
    tile_width: int = 16
    tile_height: int = 16
    image_path: str = ""
    image_width: int = 0
    image_height: int = 0
    columns: int = 1
    tile_count: int = 0
    properties: dict[int, dict[str, Any]] = field(default_factory=dict)

    def get_tile_region(self, local_id: int) -> tuple[int, int, int, int]:
        """Get texture region for a local tile ID."""
        col = local_id % self.columns
        row = local_id // self.columns
        return (
            col * self.tile_width,
            row * self.tile_height,
            self.tile_width,
            self.tile_height,
        )

    def get_tile_properties(self, local_id: int) -> dict[str, Any]:
        """Get properties for a tile."""
        return self.properties.get(local_id, {})


@dataclass
class SpawnPoint:
    """An entity spawn point on the map."""
    name: str = ""
    entity_type: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 16.0
    height: float = 16.0
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class MapTransition:
    """A transition zone to another map."""
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    width: float = 16.0
    height: float = 16.0
    target_map: str = ""
    target_spawn: str = ""
    transition_type: str = "fade"


class GameMap:
    """
    Represents a game map loaded from Tiled.

    Handles:
    - Loading from Tiled JSON format
    - Tile collision detection
    - Object/spawn point management
    - Map transitions
    """

    def __init__(self):
        self.name: str = ""
        self.file_path: Optional[Path] = None

        # Dimensions
        self.width: int = 0  # In tiles
        self.height: int = 0
        self.tile_width: int = 16
        self.tile_height: int = 16

        # Map data
        self.layers: list[MapLayer] = []
        self.tilesets: list[MapTileset] = []
        self.properties: dict[str, Any] = {}

        # Collision
        self.collision_layer: Optional[list[list[bool]]] = None
        self.tile_properties: dict[int, set[TileProperty]] = {}

        # Objects
        self.spawn_points: dict[str, SpawnPoint] = {}
        self.transitions: list[MapTransition] = []

        # Cached data
        self._entities_spawned: bool = False

    @property
    def pixel_width(self) -> int:
        """Map width in pixels."""
        return self.width * self.tile_width

    @property
    def pixel_height(self) -> int:
        """Map height in pixels."""
        return self.height * self.tile_height

    @classmethod
    def load(cls, path: str | Path) -> GameMap:
        """Load a map from Tiled JSON format."""
        path = Path(path)
        map_obj = cls()
        map_obj.file_path = path
        map_obj.name = path.stem

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        map_obj._parse_tiled_json(data, path.parent)
        return map_obj

    def _parse_tiled_json(self, data: dict, base_path: Path) -> None:
        """Parse Tiled JSON data."""
        # Map properties
        self.width = data.get('width', 0)
        self.height = data.get('height', 0)
        self.tile_width = data.get('tilewidth', 16)
        self.tile_height = data.get('tileheight', 16)
        self.properties = self._parse_properties(data.get('properties', []))

        # Parse tilesets
        for ts_data in data.get('tilesets', []):
            tileset = self._parse_tileset(ts_data, base_path)
            self.tilesets.append(tileset)

        # Parse layers
        for layer_data in data.get('layers', []):
            layer = self._parse_layer(layer_data)
            self.layers.append(layer)

        # Build collision map
        self._build_collision()

    def _parse_tileset(self, data: dict, base_path: Path) -> MapTileset:
        """Parse a tileset reference."""
        tileset = MapTileset()
        tileset.first_gid = data.get('firstgid', 1)

        # Handle external tileset
        if 'source' in data:
            ts_path = base_path / data['source']
            with open(ts_path, 'r', encoding='utf-8') as f:
                ts_data = json.load(f)
            data = {**ts_data, 'firstgid': tileset.first_gid}

        tileset.name = data.get('name', '')
        tileset.tile_width = data.get('tilewidth', 16)
        tileset.tile_height = data.get('tileheight', 16)
        tileset.columns = data.get('columns', 1)
        tileset.tile_count = data.get('tilecount', 0)

        if 'image' in data:
            tileset.image_path = data['image']
            tileset.image_width = data.get('imagewidth', 0)
            tileset.image_height = data.get('imageheight', 0)

        # Parse tile properties
        for tile_data in data.get('tiles', []):
            tile_id = tile_data.get('id', 0)
            props = self._parse_properties(tile_data.get('properties', []))
            tileset.properties[tile_id] = props

        return tileset

    def _parse_layer(self, data: dict) -> MapLayer:
        """Parse a map layer."""
        layer = MapLayer()
        layer.name = data.get('name', '')
        layer.layer_type = data.get('type', 'tilelayer')
        layer.visible = data.get('visible', True)
        layer.opacity = data.get('opacity', 1.0)
        layer.offset_x = data.get('offsetx', 0.0)
        layer.offset_y = data.get('offsety', 0.0)
        layer.parallax_x = data.get('parallaxx', 1.0)
        layer.parallax_y = data.get('parallaxy', 1.0)
        layer.properties = self._parse_properties(data.get('properties', []))

        if layer.layer_type == 'tilelayer':
            self._parse_tile_layer(layer, data)
        elif layer.layer_type == 'objectgroup':
            self._parse_object_layer(layer, data)

        return layer

    def _parse_tile_layer(self, layer: MapLayer, data: dict) -> None:
        """Parse tile data for a layer."""
        width = data.get('width', self.width)
        height = data.get('height', self.height)
        tile_data = data.get('data', [])

        # Convert flat array to 2D grid
        layer.tiles = []
        for y in range(height):
            row = []
            for x in range(width):
                idx = y * width + x
                gid = tile_data[idx] if idx < len(tile_data) else 0

                # Extract flip flags from GID
                FLIP_H = 0x80000000
                FLIP_V = 0x40000000
                FLIP_D = 0x20000000

                flip_h = bool(gid & FLIP_H)
                flip_v = bool(gid & FLIP_V)
                flip_d = bool(gid & FLIP_D)

                # Clear flip bits to get actual GID
                actual_gid = gid & ~(FLIP_H | FLIP_V | FLIP_D)

                row.append(MapTile(
                    gid=actual_gid,
                    flip_h=flip_h,
                    flip_v=flip_v,
                    flip_d=flip_d,
                ))
            layer.tiles.append(row)

    def _parse_object_layer(self, layer: MapLayer, data: dict) -> None:
        """Parse objects in an object layer."""
        for obj_data in data.get('objects', []):
            obj = {
                'id': obj_data.get('id', 0),
                'name': obj_data.get('name', ''),
                'type': obj_data.get('type', ''),
                'x': obj_data.get('x', 0),
                'y': obj_data.get('y', 0),
                'width': obj_data.get('width', 0),
                'height': obj_data.get('height', 0),
                'rotation': obj_data.get('rotation', 0),
                'visible': obj_data.get('visible', True),
                'properties': self._parse_properties(obj_data.get('properties', [])),
            }
            layer.objects.append(obj)

            # Handle special object types
            obj_type = obj['type'].lower()

            if obj_type == 'spawn':
                spawn = SpawnPoint(
                    name=obj['name'],
                    entity_type=obj['properties'].get('entity_type', ''),
                    x=obj['x'],
                    y=obj['y'],
                    width=obj['width'],
                    height=obj['height'],
                    properties=obj['properties'],
                )
                self.spawn_points[spawn.name] = spawn

            elif obj_type == 'transition':
                transition = MapTransition(
                    name=obj['name'],
                    x=obj['x'],
                    y=obj['y'],
                    width=obj['width'],
                    height=obj['height'],
                    target_map=obj['properties'].get('target_map', ''),
                    target_spawn=obj['properties'].get('target_spawn', ''),
                    transition_type=obj['properties'].get('transition', 'fade'),
                )
                self.transitions.append(transition)

    def _parse_properties(self, props_list: list) -> dict[str, Any]:
        """Parse Tiled properties array into dict."""
        result = {}
        for prop in props_list:
            name = prop.get('name', '')
            value = prop.get('value')
            result[name] = value
        return result

    def _build_collision(self) -> None:
        """Build collision map from layers marked as collision."""
        self.collision_layer = [
            [False for _ in range(self.width)]
            for _ in range(self.height)
        ]

        for layer in self.layers:
            if layer.layer_type != 'tilelayer':
                continue

            # Check if this is a collision layer
            is_collision = layer.properties.get('collision', False)
            if not is_collision and 'collision' not in layer.name.lower():
                continue

            for y, row in enumerate(layer.tiles):
                for x, tile in enumerate(row):
                    if tile.gid > 0:
                        self.collision_layer[y][x] = True

    def is_solid(self, tile_x: int, tile_y: int) -> bool:
        """Check if a tile position is solid."""
        if not self.collision_layer:
            return False

        if tile_x < 0 or tile_x >= self.width:
            return True
        if tile_y < 0 or tile_y >= self.height:
            return True

        return self.collision_layer[tile_y][tile_x]

    def is_solid_pixel(self, x: float, y: float) -> bool:
        """Check if a pixel position is solid."""
        tile_x = int(x // self.tile_width)
        tile_y = int(y // self.tile_height)
        return self.is_solid(tile_x, tile_y)

    def get_solid_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float
    ) -> bool:
        """Check if a rectangle intersects any solid tiles."""
        left = int(x // self.tile_width)
        top = int(y // self.tile_height)
        right = int((x + width - 1) // self.tile_width)
        bottom = int((y + height - 1) // self.tile_height)

        for ty in range(top, bottom + 1):
            for tx in range(left, right + 1):
                if self.is_solid(tx, ty):
                    return True
        return False

    def get_spawn_point(self, name: str) -> Optional[SpawnPoint]:
        """Get a spawn point by name."""
        return self.spawn_points.get(name)

    def get_transition_at(self, x: float, y: float) -> Optional[MapTransition]:
        """Get transition zone at a pixel position."""
        for transition in self.transitions:
            if (transition.x <= x < transition.x + transition.width and
                transition.y <= y < transition.y + transition.height):
                return transition
        return None

    def get_layer(self, name: str) -> Optional[MapLayer]:
        """Get a layer by name."""
        for layer in self.layers:
            if layer.name == name:
                return layer
        return None

    def get_tileset_for_gid(self, gid: int) -> Optional[MapTileset]:
        """Get the tileset that contains a global tile ID."""
        result = None
        for tileset in self.tilesets:
            if gid >= tileset.first_gid:
                if result is None or tileset.first_gid > result.first_gid:
                    result = tileset
        return result

    def get_tile_local_id(self, gid: int) -> tuple[Optional[MapTileset], int]:
        """Get tileset and local ID for a global ID."""
        tileset = self.get_tileset_for_gid(gid)
        if tileset:
            return tileset, gid - tileset.first_gid
        return None, 0


class MapManager:
    """
    Manages loading and caching maps.
    """

    def __init__(self, game: Game, maps_path: str = "game/data/maps"):
        self.game = game
        self.maps_path = Path(maps_path)
        self._cache: dict[str, GameMap] = {}
        self.current_map: Optional[GameMap] = None

    def load(self, map_name: str) -> GameMap:
        """Load a map by name."""
        if map_name in self._cache:
            return self._cache[map_name]

        # Try different extensions
        for ext in ['.tmj', '.json']:
            path = self.maps_path / f"{map_name}{ext}"
            if path.exists():
                game_map = GameMap.load(path)
                self._cache[map_name] = game_map
                return game_map

        raise FileNotFoundError(f"Map not found: {map_name}")

    def set_current(self, map_name: str) -> GameMap:
        """Set the current active map."""
        self.current_map = self.load(map_name)
        return self.current_map

    def clear_cache(self) -> None:
        """Clear the map cache."""
        self._cache.clear()
