import pytest
from unittest.mock import MagicMock, patch
from engine.graphics.context import GraphicsContext

def test_graphics_context_init(mock_moderngl):
    ctx = GraphicsContext(mock_moderngl)
    assert ctx.ctx is mock_moderngl
    
def test_create_program(mock_moderngl):
    ctx = GraphicsContext(mock_moderngl)
    
    # Mock ctx.program result
    mock_prog = MagicMock()
    mock_moderngl.program.return_value = mock_prog
    
    prog = ctx.create_program("vert", "frag")
    assert prog is mock_prog
    mock_moderngl.program.assert_called_with(
        vertex_shader="vert",
        fragment_shader="frag",
        geometry_shader=None
    )

def test_clear(mock_moderngl):
    ctx = GraphicsContext(mock_moderngl)
    ctx.clear(0.1, 0.2, 0.3, 1.0)
    mock_moderngl.clear.assert_called_with(0.1, 0.2, 0.3, 1.0)
