import sys
import os

# Ensure we can import from root
sys.path.append(os.getcwd())

import pygame
# Force dummy driver for headless environment
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SDL_VIDEODRIVER"] = "dummy"

from engine.audio import AudioManager, MusicPlayer, AudioSource, AudioListener, AudioSystem
from framework.components.transform import Transform

def run_tests():
    print("=== Verifying Audio System ===")
    
    # 1. Component Instantiation
    print("[1] Testing Components...")
    source = AudioSource(sound_id="boom.wav", volume=0.8, loop=True)
    assert source.sound_id == "boom.wav"
    assert source.volume == 0.8
    assert source.loop is True
    assert source.spatial is True  # default
    assert source._channel is None
    print("    AudioSource OK")
    
    listener = AudioListener()
    assert listener.active is True
    print("    AudioListener OK")
    
    # 2. Manager Initialization
    print("[2] Testing AudioManager...")
    manager = AudioManager()
    
    # Needs pygame init
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    
    manager.init()
    print("    Init OK")
    
    # Check settings
    manager.set_master_volume(0.5)
    settings = manager.get_settings()
    assert settings["master"] == 0.5
    print("    Settings OK")
    
    # 3. AudioSystem
    print("[3] Testing AudioSystem...")
    system = AudioSystem(manager)
    assert system.audio_manager == manager
    print("    AudioSystem OK")
    
    manager.quit()
    pygame.quit()
    
    print("\nALL TESTS PASSED")

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"\nFAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
