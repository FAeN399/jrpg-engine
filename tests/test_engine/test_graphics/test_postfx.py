import pytest
from unittest.mock import MagicMock, patch
from engine.graphics.postfx import PostProcessingChain, BloomEffect

@pytest.fixture
def mock_ctx(mock_moderngl):
    return mock_moderngl

def test_postfx_chain_init(mock_ctx):
    # Mock file reading
    with patch('pathlib.Path.read_text', return_value="shader_source"):
        chain = PostProcessingChain(mock_ctx, 800, 600)
    
    assert chain.width == 800
    assert chain.height == 600

def test_enable_bloom(mock_ctx):
    with patch('pathlib.Path.read_text', return_value="shader_source"):
        chain = PostProcessingChain(mock_ctx, 800, 600)
        bloom = chain.enable_bloom()
        
    assert isinstance(bloom, BloomEffect)
    assert chain.bloom is bloom

def test_resize(mock_ctx):
    with patch('pathlib.Path.read_text', return_value="shader_source"):
        chain = PostProcessingChain(mock_ctx, 800, 600)
        
    chain.resize(1024, 768)
    assert chain.width == 1024
    assert chain.height == 768
    # Framebuffers should be recreated which implies calls to texture/framebuffer
    assert mock_ctx.texture.call_count >= 2 # Initial + Resize
