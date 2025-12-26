import pytest
from unittest.mock import MagicMock, patch, mock_open
import json
from pathlib import Path
from engine.resources.database import Database

@pytest.fixture
def mock_db_path(tmp_path):
    # Setup mock directory structure in tmp_path
    schemas = tmp_path / "schemas"
    schemas.mkdir()
    
    database = tmp_path / "database"
    database.mkdir()
    (database / "items").mkdir()
    
    # Create valid schema
    item_schema = {
        "type": "object",
        "required": ["id", "price"],
        "properties": {
            "id": {"type": "string"},
            "price": {"type": "integer"}
        }
    }
    with open(schemas / "item.schema.json", "w") as f:
        json.dump(item_schema, f)
        
    return tmp_path

def test_load_all(mock_db_path):
    # Create valid item
    item_data = [
        {"id": "sword", "price": 100}
    ]
    with open(mock_db_path / "database" / "items" / "sword.json", "w") as f:
        json.dump(item_data, f)
        
    db = Database(mock_db_path)
    db.load_all()
    
    assert "sword" in db.items
    assert db.items["sword"]["price"] == 100

def test_validation_error(mock_db_path):
    # Create invalid item (missing price)
    item_data = [
        {"id": "broken"}
    ]
    with open(mock_db_path / "database" / "items" / "broken.json", "w") as f:
        json.dump(item_data, f)
        
    db = Database(mock_db_path)
    db.load_all()
    
    assert "broken" not in db.items # Should be skipped due to validation error

def test_missing_schema(mock_db_path):
    # Create item but delete schema
    item_data = [{"id": "sword", "price": 100}]
    with open(mock_db_path / "database" / "items" / "sword.json", "w") as f:
        json.dump(item_data, f)
    
    (mock_db_path / "schemas" / "item.schema.json").unlink()
    
    db = Database(mock_db_path)
    db.load_all()
    
    # Without schema, it might skip loading or load without validation depending on implementation
    # Current implementation logs warning and skips if schema not found
    assert "sword" not in db.items 
