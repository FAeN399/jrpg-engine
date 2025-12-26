"""
Animation system - processes animated sprites.

Handles:
- Animation playback advancement
- Frame events
- Animation transitions
- Directional animation selection
- Flash effects
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Dict, Optional, Callable, Any

from engine.core import System, World, EventBus, Event
from engine.graphics.animation import (
    AnimationSet,
    AnimationClip,
    AnimationFrame,
    LoopMode,
)
from engine.graphics.animator import AnimationLoader, AnimationManager
from framework.components.animated_sprite import (
    AnimatedSprite,
    SpriteFlash,
)
from framework.components.transform import Transform, Direction

if TYPE_CHECKING:
    from engine.core.entity import Entity


class AnimationEvent(Enum):
    """Animation system events."""
    ANIMATION_STARTED = auto()   # clip_name, entity_id
    ANIMATION_COMPLETED = auto()  # clip_name, entity_id
    ANIMATION_LOOPED = auto()     # clip_name, entity_id
    FRAME_EVENT = auto()          # event_name, clip_name, entity_id


class AnimationSystem(System):
    """
    Processes animation for all entities with AnimatedSprite component.

    Features:
    - Manages animation sets by name
    - Updates animation time and frame selection
    - Fires frame events through EventBus
    - Handles directional animation selection
    - Processes flash effects
    """

    def __init__(
        self,
        world: World,
        event_bus: Optional[EventBus] = None,
        base_path: str = "",
    ):
        super().__init__()
        self._world = world
        self._event_bus = event_bus
        self._animation_manager = AnimationManager(base_path)

        # Custom frame event handlers
        self._frame_event_handlers: Dict[str, Callable[[int, str], None]] = {}

        self.required_components = {AnimatedSprite}

    @property
    def world(self) -> World:
        """Get the world."""
        return self._world

    @property
    def animation_manager(self) -> AnimationManager:
        """Get the animation manager."""
        return self._animation_manager

    # Animation set management

    def register_animation_set(self, name: str, anim_set: AnimationSet) -> None:
        """Register an animation set by name."""
        self._animation_manager.register(name, anim_set)

    def load_animation_set(self, name: str, path: str) -> AnimationSet:
        """Load animation set from JSON file."""
        return self._animation_manager.load(name, path)

    def get_animation_set(self, name: str) -> Optional[AnimationSet]:
        """Get registered animation set."""
        return self._animation_manager.get(name)

    def create_animation_set(self, name: str) -> AnimationSet:
        """Create a new empty animation set."""
        return self._animation_manager.create(name)

    # Frame event handling

    def register_frame_event_handler(
        self,
        event_name: str,
        handler: Callable[[int, str], None],
    ) -> None:
        """
        Register a handler for frame events.

        Args:
            event_name: The event name to handle
            handler: Callback(entity_id, clip_name)
        """
        self._frame_event_handlers[event_name] = handler

    def unregister_frame_event_handler(self, event_name: str) -> None:
        """Remove a frame event handler."""
        self._frame_event_handlers.pop(event_name, None)

    # Animation control (for convenience)

    def play(
        self,
        entity_id: int,
        clip_name: str,
        restart: bool = False,
    ) -> bool:
        """
        Play an animation clip on an entity.

        Args:
            entity_id: The entity ID
            clip_name: Name of clip to play
            restart: Restart if already playing this clip

        Returns:
            True if animation was started
        """
        entity = self._world.get_entity(entity_id)
        if not entity:
            return False

        sprite = entity.try_get(AnimatedSprite)
        if not sprite:
            return False

        # Check if already playing
        if not restart and sprite.current_clip == clip_name:
            return True

        # Get animation set
        anim_set = self._animation_manager.get(sprite.animation_set_name)
        if not anim_set or not anim_set.has_clip(clip_name):
            return False

        # Set up new animation
        sprite.current_clip = clip_name
        sprite.current_time = 0.0
        sprite.current_frame_index = 0
        sprite.playing = True
        sprite.completed = False

        # Fire event
        if self._event_bus:
            self._event_bus.publish(
                AnimationEvent.ANIMATION_STARTED,
                entity_id=entity_id,
                clip_name=clip_name,
            )

        return True

    def play_directional(
        self,
        entity_id: int,
        base_name: str,
        direction: Optional[Direction] = None,
    ) -> bool:
        """
        Play a directional animation based on entity facing.

        Args:
            entity_id: The entity ID
            base_name: Base animation name (e.g., 'walk')
            direction: Override direction (or use Transform.facing)

        Returns:
            True if animation was started
        """
        entity = self._world.get_entity(entity_id)
        if not entity:
            return False

        # Get direction
        if direction is None:
            transform = entity.try_get(Transform)
            direction = transform.facing if transform else Direction.DOWN

        # Map direction to suffix
        dir_suffix = {
            Direction.UP: "up",
            Direction.DOWN: "down",
            Direction.LEFT: "left",
            Direction.RIGHT: "right",
            Direction.UP_LEFT: "left",
            Direction.UP_RIGHT: "right",
            Direction.DOWN_LEFT: "left",
            Direction.DOWN_RIGHT: "right",
            Direction.NONE: "down",
        }.get(direction, "down")

        clip_name = f"{base_name}_{dir_suffix}"
        return self.play(entity_id, clip_name)

    def stop(self, entity_id: int) -> None:
        """Stop animation playback."""
        entity = self._world.get_entity(entity_id)
        if entity:
            sprite = entity.try_get(AnimatedSprite)
            if sprite:
                sprite.playing = False
                sprite.current_time = 0.0
                sprite.current_frame_index = 0

    def pause(self, entity_id: int) -> None:
        """Pause animation at current frame."""
        entity = self._world.get_entity(entity_id)
        if entity:
            sprite = entity.try_get(AnimatedSprite)
            if sprite:
                sprite.playing = False

    def resume(self, entity_id: int) -> None:
        """Resume paused animation."""
        entity = self._world.get_entity(entity_id)
        if entity:
            sprite = entity.try_get(AnimatedSprite)
            if sprite:
                sprite.playing = True

    def set_speed(self, entity_id: int, speed: float) -> None:
        """Set animation playback speed."""
        entity = self._world.get_entity(entity_id)
        if entity:
            sprite = entity.try_get(AnimatedSprite)
            if sprite:
                sprite.speed = max(0.0, speed)

    # Flash effects

    def flash(
        self,
        entity_id: int,
        r: int = 255,
        g: int = 255,
        b: int = 255,
        duration: float = 0.1,
    ) -> None:
        """Apply a flash effect to an entity."""
        entity = self._world.get_entity(entity_id)
        if not entity:
            return

        sprite = entity.try_get(AnimatedSprite)
        if not sprite:
            return

        # Create or update flash component
        flash = entity.try_get(SpriteFlash)
        if flash:
            # Update existing flash
            flash.flash_r = r
            flash.flash_g = g
            flash.flash_b = b
            flash.duration = duration
            flash.elapsed = 0.0
        else:
            # Create new flash
            flash = SpriteFlash(
                flash_r=r,
                flash_g=g,
                flash_b=b,
                duration=duration,
                elapsed=0.0,
                original_tint_r=sprite.tint_r,
                original_tint_g=sprite.tint_g,
                original_tint_b=sprite.tint_b,
            )
            entity.add(flash)

        # Apply flash color immediately
        sprite.tint_r = r
        sprite.tint_g = g
        sprite.tint_b = b

    def damage_flash(self, entity_id: int) -> None:
        """Apply damage flash effect."""
        self.flash(entity_id, 255, 100, 100, 0.15)

    def heal_flash(self, entity_id: int) -> None:
        """Apply heal flash effect."""
        self.flash(entity_id, 100, 255, 100, 0.2)

    # System update

    def update(self, dt: float) -> None:
        """Update all animated sprites."""
        entities = self._world.get_entities_with(AnimatedSprite)

        for entity in entities:
            self._process_animation(entity, dt)
            self._process_flash(entity, dt)

    def _process_animation(self, entity: 'Entity', dt: float) -> None:
        """Process animation for a single entity."""
        sprite = entity.get(AnimatedSprite)
        if not sprite or not sprite.playing or not sprite.visible:
            return

        # Get animation set
        anim_set = self._animation_manager.get(sprite.animation_set_name)
        if not anim_set:
            return

        # Get current clip
        clip = anim_set.get_clip(sprite.current_clip)
        if not clip or not clip.frames:
            return

        # Advance time
        sprite.current_time += dt * sprite.speed * clip.speed_multiplier

        # Get frame at current time
        frame, frame_index = clip.get_frame_at_time(sprite.current_time)

        # Check for frame change and fire events
        if frame_index != sprite.current_frame_index:
            sprite.current_frame_index = frame_index

            if frame.event:
                self._fire_frame_event(entity.id, clip.name, frame.event)

        # Update sprite data from frame
        sprite.texture_region = frame.region_name
        sprite.offset_x = frame.offset_x
        sprite.offset_y = frame.offset_y

        # Check for completion/looping
        duration = clip.total_duration
        if duration > 0 and sprite.current_time >= duration:
            if clip.loop_mode == LoopMode.ONCE:
                sprite.playing = False
                sprite.completed = True
                sprite.current_time = duration

                if self._event_bus:
                    self._event_bus.publish(
                        AnimationEvent.ANIMATION_COMPLETED,
                        entity_id=entity.id,
                        clip_name=clip.name,
                    )
            else:
                # Looping
                if self._event_bus:
                    self._event_bus.publish(
                        AnimationEvent.ANIMATION_LOOPED,
                        entity_id=entity.id,
                        clip_name=clip.name,
                    )

    def _process_flash(self, entity: 'Entity', dt: float) -> None:
        """Process flash effect for an entity."""
        flash = entity.try_get(SpriteFlash)
        if not flash:
            return

        sprite = entity.try_get(AnimatedSprite)
        if not sprite:
            entity.remove(SpriteFlash)
            return

        flash.elapsed += dt

        if flash.elapsed >= flash.duration:
            # Restore original tint and remove flash
            sprite.tint_r = flash.original_tint_r
            sprite.tint_g = flash.original_tint_g
            sprite.tint_b = flash.original_tint_b
            entity.remove(SpriteFlash)
        else:
            # Interpolate between flash and original
            t = flash.elapsed / flash.duration
            sprite.tint_r = int(flash.flash_r + (flash.original_tint_r - flash.flash_r) * t)
            sprite.tint_g = int(flash.flash_g + (flash.original_tint_g - flash.flash_g) * t)
            sprite.tint_b = int(flash.flash_b + (flash.original_tint_b - flash.flash_b) * t)

    def _fire_frame_event(
        self,
        entity_id: int,
        clip_name: str,
        event_name: str,
    ) -> None:
        """Fire a frame event."""
        # Call registered handler
        handler = self._frame_event_handlers.get(event_name)
        if handler:
            try:
                handler(entity_id, clip_name)
            except Exception as e:
                print(f"Error in frame event handler '{event_name}': {e}")

        # Publish to event bus
        if self._event_bus:
            self._event_bus.publish(
                AnimationEvent.FRAME_EVENT,
                entity_id=entity_id,
                clip_name=clip_name,
                event_name=event_name,
            )

    def process_entity(self, entity: 'Entity', dt: float) -> None:
        """Process a single entity (required by System base class)."""
        self._process_animation(entity, dt)
        self._process_flash(entity, dt)
