"""
System for updating audio sources.
"""

from __future__ import annotations

import pygame
from engine.core.system import System
from engine.core.entity import Entity
from engine.audio.components import AudioSource, AudioListener
from engine.audio.manager import AudioManager
from framework.components.transform import Transform


class AudioSystem(System):
    """
    Updates AudioSource components.
    
    - Starts/Stops sounds based on .active state.
    - Updates spatial position for 2D panning.
    """
    required_components = [AudioSource, Transform]

    def __init__(self, audio_manager: AudioManager):
        super().__init__()
        self.audio_manager = audio_manager
        self._listener_transform: Transform | None = None

    def pre_update(self, dt: float) -> None:
        """Find the listener before processing sources."""
        # Find active listener
        self._listener_transform = None
        
        # We need to iterate all entities with AudioListener
        # Since System.get_entities() only returns those matching *required_components*,
        # we need to query the world manually for Listeners.
        if self._world:
             # This assumes world has a way to query. 
             # Standard ECS pattern: world.get_entities_with(AudioListener, Transform)
             listeners = self._world.get_entities_with(AudioListener, Transform)
             for entity in listeners:
                 listener = entity.get(AudioListener)
                 if listener.active:
                     self._listener_transform = entity.get(Transform)
                     # Update manager's listener pos
                     self.audio_manager.set_listener_position(self._listener_transform.position)
                     break

    def process_entity(self, entity: Entity, dt: float) -> None:
        source = entity.get(AudioSource)
        transform = entity.get(Transform)

        # Handle State Changes
        if source.active and source._channel is None:
            # Start playing
            loops = -1 if source.loop else 0
            channel = self.audio_manager.play_sfx(
                source.sound_id,
                position=transform.position if source.spatial else None,
                category=source.category,
                volume=source.volume,
                loops=loops
            )
            if channel:
                source._channel = channel
            else:
                # Failed to play (no channels?), disable source to prevent retry spam
                # source.active = False 
                pass

        elif not source.active and source._channel is not None:
            # Stop playing
            source._channel.stop()
            source._channel = None

        # Update Active Sources
        if source.active and source._channel is not None:
            channel = source._channel
            
            # Check if channel finished playing (for non-looping sounds)
            if not channel.get_busy():
                source._channel = None
                source.active = False
                return

            # Update Spatial Audio
            if source.spatial:
                # Re-calculate volume/pan
                # We need to call a method on AudioManager to recalc channel vol
                # But AudioManager doesn't expose "update channel".
                # We can recalculate manually or expose a helper.
                # Let's use the helper on manager if possible? 
                # Manager.play_sfx does the calc but returns a channel.
                # We can reuse the _calculate_spatial_volume method if we make it public or duplicate logic?
                # Ideally, AudioManager should handle this.
                # Let's call a new method on AudioManager: update_channel_spatial(channel, pos)
                # But I defined `_calculate_spatial_volume` as protected. 
                # I'll just access it or duplicate simple logic. Accessing protected is OK within the module/package context often.
                
                if self._listener_transform:
                    l_vol, r_vol = self.audio_manager._calculate_spatial_volume(
                        transform.position,
                        self._listener_transform.position,
                        source.max_distance
                    )
                    
                    # Apply master/category/source volumes again?
                    # Channel.set_volume sets the multiplier on the Sound's volume?
                    # No, set_volume(left, right) sets the channel volume.
                    # We need the base volume.
                    
                    base_vol = self.audio_manager._master_volume * \
                               self.audio_manager._category_volumes.get(source.category, 1.0) * \
                               source.volume
                               
                    channel.set_volume(base_vol * l_vol, base_vol * r_vol)
