"""
Quest system - tracking, objectives, rewards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum, auto
import json
from pathlib import Path


class QuestStatus(Enum):
    """Quest progress status."""
    UNKNOWN = auto()      # Not discovered
    AVAILABLE = auto()    # Can be started
    ACTIVE = auto()       # Currently in progress
    COMPLETED = auto()    # All objectives done
    TURNED_IN = auto()    # Rewards claimed
    FAILED = auto()       # Quest failed


class ObjectiveType(Enum):
    """Types of quest objectives."""
    TALK = auto()         # Talk to NPC
    COLLECT = auto()      # Collect items
    KILL = auto()         # Defeat enemies
    DELIVER = auto()      # Deliver item to NPC
    REACH = auto()        # Reach a location
    INTERACT = auto()     # Interact with object
    CUSTOM = auto()       # Custom scripted


@dataclass
class QuestObjective:
    """A single quest objective."""
    id: str
    objective_type: ObjectiveType
    description: str = ""

    # Target
    target_id: str = ""       # NPC, enemy type, item, location, etc.
    target_count: int = 1     # How many needed
    current_count: int = 0    # Current progress

    # State
    is_complete: bool = False
    is_optional: bool = False
    is_hidden: bool = False

    @property
    def progress(self) -> float:
        """Get progress as percentage."""
        if self.target_count <= 0:
            return 1.0 if self.is_complete else 0.0
        return min(1.0, self.current_count / self.target_count)

    def update_progress(self, amount: int = 1) -> bool:
        """
        Update objective progress.

        Returns:
            True if objective became complete
        """
        if self.is_complete:
            return False

        self.current_count = min(self.current_count + amount, self.target_count)

        if self.current_count >= self.target_count:
            self.is_complete = True
            return True

        return False


@dataclass
class QuestReward:
    """Rewards for completing a quest."""
    exp: int = 0
    gold: int = 0
    items: list[tuple[str, int]] = field(default_factory=list)  # (item_id, count)
    unlocks_quests: list[str] = field(default_factory=list)


@dataclass
class Quest:
    """A complete quest definition."""
    id: str
    name: str
    description: str = ""

    # Status
    status: QuestStatus = QuestStatus.UNKNOWN

    # Objectives
    objectives: list[QuestObjective] = field(default_factory=list)

    # Requirements
    required_level: int = 1
    required_quests: list[str] = field(default_factory=list)

    # Rewards
    rewards: QuestReward = field(default_factory=QuestReward)

    # NPCs
    quest_giver: str = ""     # NPC who gives quest
    turn_in_npc: str = ""     # NPC to turn in to (default: quest_giver)

    # Tracking
    is_main_quest: bool = False
    is_repeatable: bool = False

    @property
    def is_complete(self) -> bool:
        """Check if all required objectives are complete."""
        for obj in self.objectives:
            if not obj.is_optional and not obj.is_complete:
                return False
        return True

    def get_current_objective(self) -> Optional[QuestObjective]:
        """Get the first incomplete objective."""
        for obj in self.objectives:
            if not obj.is_complete and not obj.is_hidden:
                return obj
        return None


class QuestManager:
    """
    Manages quest tracking and progression.
    """

    def __init__(self, data_path: str = "game/data/database"):
        self.data_path = Path(data_path)

        # Quest templates
        self._quest_templates: dict[str, Quest] = {}

        # Active quest instances
        self._active_quests: dict[str, Quest] = {}

        # Completed quest IDs
        self._completed_quests: set[str] = set()

    def load_quests(self, filename: str = "quests.json") -> None:
        """Load quest definitions from JSON."""
        path = self.data_path / filename
        if not path.exists():
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for quest_data in data.get('quests', []):
            quest = self._parse_quest(quest_data)
            self._quest_templates[quest.id] = quest

    def _parse_quest(self, data: dict) -> Quest:
        """Parse a quest from JSON data."""
        quest = Quest(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            required_level=data.get('required_level', 1),
            required_quests=data.get('required_quests', []),
            quest_giver=data.get('quest_giver', ''),
            turn_in_npc=data.get('turn_in_npc', data.get('quest_giver', '')),
            is_main_quest=data.get('is_main_quest', False),
            is_repeatable=data.get('is_repeatable', False),
        )

        # Parse objectives
        for obj_data in data.get('objectives', []):
            obj = QuestObjective(
                id=obj_data['id'],
                objective_type=ObjectiveType[obj_data.get('type', 'CUSTOM').upper()],
                description=obj_data.get('description', ''),
                target_id=obj_data.get('target', ''),
                target_count=obj_data.get('count', 1),
                is_optional=obj_data.get('optional', False),
                is_hidden=obj_data.get('hidden', False),
            )
            quest.objectives.append(obj)

        # Parse rewards
        if 'rewards' in data:
            rewards = data['rewards']
            quest.rewards = QuestReward(
                exp=rewards.get('exp', 0),
                gold=rewards.get('gold', 0),
                items=[(i['id'], i.get('count', 1)) for i in rewards.get('items', [])],
                unlocks_quests=rewards.get('unlocks', []),
            )

        return quest

    def start_quest(self, quest_id: str) -> bool:
        """Start a quest."""
        if quest_id in self._active_quests:
            return False  # Already active

        template = self._quest_templates.get(quest_id)
        if not template:
            return False

        # Create instance from template
        import copy
        quest = copy.deepcopy(template)
        quest.status = QuestStatus.ACTIVE

        self._active_quests[quest_id] = quest
        return True

    def complete_quest(self, quest_id: str) -> Optional[QuestReward]:
        """
        Complete a quest and get rewards.

        Returns:
            Rewards if quest was completed, None if not
        """
        quest = self._active_quests.get(quest_id)
        if not quest or not quest.is_complete:
            return None

        quest.status = QuestStatus.TURNED_IN
        rewards = quest.rewards

        # Move to completed
        del self._active_quests[quest_id]
        self._completed_quests.add(quest_id)

        # Unlock new quests
        for unlock_id in rewards.unlocks_quests:
            template = self._quest_templates.get(unlock_id)
            if template:
                template.status = QuestStatus.AVAILABLE

        return rewards

    def update_objective(
        self,
        objective_type: ObjectiveType,
        target_id: str,
        amount: int = 1,
    ) -> list[str]:
        """
        Update objective progress across all active quests.

        Returns:
            List of quest IDs that had objectives completed
        """
        updated = []

        for quest_id, quest in self._active_quests.items():
            for obj in quest.objectives:
                if obj.objective_type == objective_type and obj.target_id == target_id:
                    if obj.update_progress(amount):
                        updated.append(quest_id)

                        # Check if quest is now complete
                        if quest.is_complete:
                            quest.status = QuestStatus.COMPLETED

        return updated

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """Get an active quest."""
        return self._active_quests.get(quest_id)

    def get_active_quests(self) -> list[Quest]:
        """Get all active quests."""
        return list(self._active_quests.values())

    def get_completed_quests(self) -> set[str]:
        """Get completed quest IDs."""
        return self._completed_quests.copy()

    def is_quest_complete(self, quest_id: str) -> bool:
        """Check if a quest is complete."""
        return quest_id in self._completed_quests

    def is_quest_active(self, quest_id: str) -> bool:
        """Check if a quest is active."""
        return quest_id in self._active_quests

    def can_start_quest(self, quest_id: str, player_level: int = 1) -> bool:
        """Check if a quest can be started."""
        if quest_id in self._active_quests:
            return False

        if quest_id in self._completed_quests:
            template = self._quest_templates.get(quest_id)
            if not template or not template.is_repeatable:
                return False

        template = self._quest_templates.get(quest_id)
        if not template:
            return False

        # Check level
        if player_level < template.required_level:
            return False

        # Check required quests
        for req in template.required_quests:
            if req not in self._completed_quests:
                return False

        return True

    def get_save_data(self) -> dict:
        """Get save data for quests."""
        return {
            'active': {
                qid: {
                    'status': q.status.name,
                    'objectives': [
                        {
                            'id': o.id,
                            'current': o.current_count,
                            'complete': o.is_complete,
                        }
                        for o in q.objectives
                    ],
                }
                for qid, q in self._active_quests.items()
            },
            'completed': list(self._completed_quests),
        }

    def load_save_data(self, data: dict) -> None:
        """Load quest state from save data."""
        self._completed_quests = set(data.get('completed', []))

        for quest_id, quest_data in data.get('active', {}).items():
            if self.start_quest(quest_id):
                quest = self._active_quests[quest_id]
                quest.status = QuestStatus[quest_data.get('status', 'ACTIVE')]

                for obj_data in quest_data.get('objectives', []):
                    for obj in quest.objectives:
                        if obj.id == obj_data['id']:
                            obj.current_count = obj_data.get('current', 0)
                            obj.is_complete = obj_data.get('complete', False)
