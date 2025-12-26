"""
Game Database.

Handles loading and validation of static game data (items, enemies, etc.).
"""

import json
import logging
from pathlib import Path
from typing import Any, TypeVar, Generic

import jsonschema

T = TypeVar('T')

class Database:
    """
    Central storage for static game data.
    """

    def __init__(self, data_path: Path | str):
        self._data_path = Path(data_path)
        self._schemas: dict[str, Any] = {}
        
        # Data stores
        self.items: dict[str, Any] = {}
        self.enemies: dict[str, Any] = {}
        self.skills: dict[str, Any] = {}
        self.quests: dict[str, Any] = {}
        self.dialogs: dict[str, Any] = {}
        
        self.logger = logging.getLogger(__name__)

    def load_all(self) -> None:
        """Load all data from disk."""
        self._load_schemas()
        
        self.items = self._load_category("items", "item.schema.json")
        self.enemies = self._load_category("enemies", "enemy.schema.json")
        self.skills = self._load_category("skills", "skill.schema.json")
        self.quests = self._load_category("quests", "quest.schema.json")
        self.dialogs = self._load_category("dialog", "dialog.schema.json")
        
        self.logger.info(
            f"Loaded {len(self.items)} items, "
            f"{len(self.enemies)} enemies, "
            f"{len(self.skills)} skills, "
            f"{len(self.quests)} quests, "
            f"{len(self.dialogs)} dialogs."
        )

    def _load_schemas(self) -> None:
        """Load JSON schemas."""
        schema_dir = self._data_path / "schemas"
        if not schema_dir.exists():
            self.logger.warning(f"Schema directory not found: {schema_dir}")
            return

        for schema_file in schema_dir.glob("*.schema.json"):
            try:
                with open(schema_file, 'r') as f:
                    schema = json.load(f)
                    self._schemas[schema_file.name] = schema
            except Exception as e:
                self.logger.error(f"Failed to load schema {schema_file}: {e}")

    def _load_category(self, folder: str, schema_name: str) -> dict[str, Any]:
        """Load all JSON files in a category folder."""
        category_dir = self._data_path / "database" / folder
        data_store: dict[str, Any] = {}
        
        if not category_dir.exists():
            self.logger.warning(f"Data directory not found: {category_dir}")
            return data_store

        schema = self._schemas.get(schema_name)
        
        for file_path in category_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                    # Validate if schema exists
                    if schema:
                        try:
                            # If file contains a list, validate each item
                            if isinstance(data, list):
                                for item in data:
                                    jsonschema.validate(instance=item, schema=schema)
                                    if 'id' in item:
                                        data_store[item['id']] = item
                            elif isinstance(data, dict):
                                jsonschema.validate(instance=data, schema=schema)
                                if 'id' in data:
                                    data_store[data['id']] = data
                        except jsonschema.ValidationError as e:
                            self.logger.error(f"Validation error in {file_path}: {e.message}")
                            continue
                    else:
                        self.logger.warning(f"No schema found for {folder} ({schema_name})")
                        
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
                
        return data_store

    def get_item(self, item_id: str) -> dict[str, Any] | None:
        return self.items.get(item_id)

    def get_enemy(self, enemy_id: str) -> dict[str, Any] | None:
        return self.enemies.get(enemy_id)
        
    def get_skill(self, skill_id: str) -> dict[str, Any] | None:
        return self.skills.get(skill_id)
