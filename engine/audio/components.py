from __future__ import annotations

from typing import Any
from pydantic import Field, PrivateAttr

from engine.core.component import Component


class AudioSource(Component):
    """
    Attach to entities that emit sounds.
    
    Attributes:
        sound_id: Resource ID of the sound to play
        volume: Playback volume (0.0 to 1.0)
        loop: Whether to loop the sound
        spatial: Whether to use 2D positional audio
        max_distance: Distance at which sound acts as max attenuation
        category: Sound category for volume control (e.g. 'sfx', 'voice')
        active: Whether the sound is currently playing/active
    """
    sound_id: str = ""
    volume: float = Field(default=1.0, ge=0.0, le=1.0)
    loop: bool = False
    spatial: bool = True
    max_distance: float = 300.0
    category: str = "sfx"
    active: bool = False
    
    # Runtime handle to the pygame channel (not serialized)
    _channel: Any = PrivateAttr(default=None)


class AudioListener(Component):
    """
    Attach to camera or player to define the 'ears' of the world.
    
    The position comes from the entity's Transform component.
    Only one active AudioListener should exist in the scene.
    """
    active: bool = True
