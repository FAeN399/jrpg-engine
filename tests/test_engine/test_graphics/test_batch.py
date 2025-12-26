import pytest
from unittest.mock import MagicMock, patch
from engine.graphics.batch import SpriteBatch

@pytest.fixture
def mock_ctx(mock_moderngl):
    return mock_moderngl

def test_sprite_batch_init(mock_ctx):
    # Mock file reading
    with patch('pathlib.Path.read_text', return_value="shader_source"):
        batch = SpriteBatch(mock_ctx)
        
    assert batch.program is not None
    mock_ctx.program.assert_called()
    mock_ctx.buffer.assert_called()

def test_sprite_batch_begin_end(mock_ctx):
    with patch('pathlib.Path.read_text', return_value="shader_source"):
        batch = SpriteBatch(mock_ctx)
    
    batch.begin()
    assert batch._drawing
    
    batch.end()
    assert not batch._drawing

def test_sprite_batch_draw(mock_ctx):
    with patch('pathlib.Path.read_text', return_value="shader_source"):
        batch = SpriteBatch(mock_ctx)
        
    batch.begin()
    
    # Mock sprite
    sprite = MagicMock()
    sprite.x = 0
    sprite.y = 0
    sprite.width = 10
    sprite.height = 10
    # Add other required fields if strictly typed, but MagicMock usually swallows attribute access.
    # Sprite dataclass is used in real code, but here we can just ensure _add_sprite_vertices is called or simple logic.
    # Actually, SpriteBatch.draw takes a Sprite object. Let's use a real Sprite.
    from engine.graphics.batch import Sprite
    s = Sprite(x=0, y=0, width=10, height=10)
    
    batch.draw(s)
    
    assert batch._sprite_count == 1
    
    batch.end()
