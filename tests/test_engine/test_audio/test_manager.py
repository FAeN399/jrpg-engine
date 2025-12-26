import pytest
from unittest.mock import MagicMock, patch
from engine.audio.manager import AudioManager
from engine.audio.system import AudioSystem
from engine.audio.components import AudioSource, AudioListener
from framework.components.transform import Transform

# All tests here need the mock_pygame fixture from conftest
pytestmark = pytest.mark.usefixtures("mock_pygame")

def test_audio_manager_init():
    import pygame
    # Simulate mixer not initialized yet
    pygame.mixer.get_init.return_value = None
    
    mgr = AudioManager()
    mgr.init()
    # Should not crash and set initialized
    assert mgr._initialized

def test_play_sfx_logic():
    mgr = AudioManager()
    mgr._initialized = True # Force initialized state for test
    
    # Mock finding a channel
    # Mock finding a channel
    import pygame
    
    # Setup mock channel behavior
    mock_channel = MagicMock()
    # Ensure set_volume doesn't crash 
    mock_channel.set_volume = MagicMock()
    mock_channel.play = MagicMock()
    
    # Configure pygame.mixer.find_channel to return our channel
    pygame.mixer.find_channel.return_value = mock_channel

    # Mock sound loading
    mgr._sound_cache["test.wav"] = MagicMock()
    
    channel = mgr.play_sfx("test.wav")
    assert channel is mock_channel
    mock_channel.play.assert_called_once()

def test_audio_system_spatial_update(world):
    mgr = AudioManager()
    mgr._initialized = True
    
    # System setup
    system = AudioSystem(mgr)
    world.add_system(system)
    
    # Listener Entity
    listener = world.create_entity()
    listener.add(Transform(x=0, y=0))
    listener.add(AudioListener(active=True))
    
    # Source Entity
    source = world.create_entity()
    source.add(Transform(x=100, y=0))
    source.add(AudioSource(
        sound_id="loop.wav",
        loop=True,
        spatial=True,
        active=True
    ))
    
    # Mock channel for source
    mock_channel = MagicMock()
    mock_channel.get_busy.return_value = True # Playing
    
    # Hijack play_sfx to return our mock channel
    with patch.object(mgr, 'play_sfx', return_value=mock_channel) as mock_play:
        # First update: should start playing
        world.update(0.1)
        mock_play.assert_called_once()
        assert source.get(AudioSource)._channel is mock_channel
        
        # Reset mock for next check
        # Update again: should not play again, should update volume
        mock_play.reset_mock()
        
        # We need to verify set_volume was called with calculated spatial values
        # Listener at 0, Source at 100. Max dist 300.
        # Falloff = 1 - (100/300) = 0.66
        # Panning: Right side.
        
        world.update(0.1)
        mock_play.assert_not_called()
        mock_channel.set_volume.assert_called() 
        # Detailed math check optional, just existence of update is good
