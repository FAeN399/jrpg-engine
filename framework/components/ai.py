"""
AI components - behavior state, patrol paths, targeting.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Optional

from pydantic import Field, PrivateAttr
from dataclasses import dataclass

from engine.core.component import Component


class AIState(Enum):
    """AI behavior states."""
    IDLE = auto()
    PATROL = auto()
    CHASE = auto()
    ATTACK = auto()
    FLEE = auto()
    RETURN = auto()
    DEAD = auto()
    SCRIPTED = auto()


class AIBehavior(Enum):
    """AI behavior archetypes."""
    NONE = auto()        # No AI
    STATIC = auto()      # Never moves
    WANDER = auto()      # Random movement
    PATROL = auto()      # Follow patrol path
    GUARD = auto()       # Stay near home, attack intruders
    AGGRESSIVE = auto()  # Seek and attack player
    COWARD = auto()      # Flee from player
    FOLLOWER = auto()    # Follow another entity


@dataclass
class PatrolPoint:
    """A single point in a patrol path."""
    x: float
    y: float
    wait_time: float = 1.0  # How long to wait at this point
    action: Optional[str] = None  # Optional action to perform


class PatrolPath(Component):
    """
    Patrol path for AI movement.

    Attributes:
        points: List of patrol points
        current_index: Current point index
        loop: Whether to loop back to start
        reverse: Patrol in reverse (ping-pong)
        wait_timer: Current wait time at point
    """
    points: list[PatrolPoint] = Field(default_factory=list)
    current_index: int = 0
    loop: bool = True
    reverse: bool = False
    wait_timer: float = 0.0
    _direction: int = PrivateAttr(default=1)  # 1 = forward, -1 = backward

    @property
    def current_point(self) -> Optional[PatrolPoint]:
        """Get current patrol point."""
        if self.points and 0 <= self.current_index < len(self.points):
            return self.points[self.current_index]
        return None

    def advance(self) -> bool:
        """
        Advance to next patrol point.

        Returns:
            True if successfully advanced, False if at end
        """
        if not self.points:
            return False

        next_index = self.current_index + self._direction

        if next_index >= len(self.points):
            if self.loop:
                if self.reverse:
                    self._direction = -1
                    self.current_index = len(self.points) - 2
                else:
                    self.current_index = 0
            else:
                return False
        elif next_index < 0:
            if self.reverse:
                self._direction = 1
                self.current_index = 1
            else:
                self.current_index = 0
        else:
            self.current_index = next_index

        # Reset wait timer
        point = self.current_point
        if point:
            self.wait_timer = point.wait_time

        return True

    def add_point(self, x: float, y: float, wait_time: float = 1.0) -> None:
        """Add a patrol point."""
        self.points.append(PatrolPoint(x=x, y=y, wait_time=wait_time))


class AIController(Component):
    """
    AI behavior controller.

    Attributes:
        behavior: Base behavior type
        state: Current AI state
        target_id: Entity ID of current target
        home_x: Home position X (for return behavior)
        home_y: Home position Y
        sight_range: Distance to detect targets
        attack_range: Distance to attack
        chase_range: Max distance to chase before returning
        move_speed: Movement speed
        think_interval: Time between AI decisions
        think_timer: Current think timer
    """
    behavior: AIBehavior = AIBehavior.NONE
    state: AIState = AIState.IDLE
    target_id: Optional[int] = None
    home_x: float = 0.0
    home_y: float = 0.0
    sight_range: float = 128.0
    attack_range: float = 16.0
    chase_range: float = 256.0
    move_speed: float = 50.0
    think_interval: float = 0.5
    think_timer: float = 0.0

    def should_think(self, dt: float) -> bool:
        """Check if AI should make a decision this frame."""
        self.think_timer -= dt
        if self.think_timer <= 0:
            self.think_timer = self.think_interval
            return True
        return False

    def set_target(self, entity_id: int) -> None:
        """Set target entity."""
        self.target_id = entity_id

    def clear_target(self) -> None:
        """Clear current target."""
        self.target_id = None

    def set_home(self, x: float, y: float) -> None:
        """Set home position."""
        self.home_x = x
        self.home_y = y

    def is_in_range(self, distance: float, range_type: str = "sight") -> bool:
        """Check if distance is within range."""
        if range_type == "sight":
            return distance <= self.sight_range
        elif range_type == "attack":
            return distance <= self.attack_range
        elif range_type == "chase":
            return distance <= self.chase_range
        return False


class Aggro(Component):
    """
    Aggression/threat tracking for combat.

    Attributes:
        threat_table: Map of entity ID to threat value
        max_entries: Maximum entries in threat table
    """
    threat_table: dict[int, float] = Field(default_factory=dict)
    max_entries: int = 10

    def add_threat(self, entity_id: int, amount: float) -> None:
        """Add threat from an entity."""
        current = self.threat_table.get(entity_id, 0.0)
        self.threat_table[entity_id] = current + amount

        # Trim if too many entries
        if len(self.threat_table) > self.max_entries:
            # Remove lowest threat entries
            sorted_threats = sorted(
                self.threat_table.items(),
                key=lambda x: x[1],
                reverse=True
            )
            self.threat_table = dict(sorted_threats[:self.max_entries])

    def get_highest_threat(self) -> Optional[int]:
        """Get entity ID with highest threat."""
        if not self.threat_table:
            return None
        return max(self.threat_table.items(), key=lambda x: x[1])[0]

    def remove_threat(self, entity_id: int) -> None:
        """Remove an entity from threat table."""
        self.threat_table.pop(entity_id, None)

    def clear_threat(self) -> None:
        """Clear all threat."""
        self.threat_table.clear()

    def decay_threat(self, factor: float) -> None:
        """Decay all threat values."""
        for entity_id in list(self.threat_table.keys()):
            self.threat_table[entity_id] *= factor
            if self.threat_table[entity_id] < 0.1:
                del self.threat_table[entity_id]
