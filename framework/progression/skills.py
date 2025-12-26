"""
Skill system - abilities, skill trees, learning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum, auto
import json
from pathlib import Path

from framework.components import CharacterClass


class SkillCategory(Enum):
    """Skill categories."""
    PHYSICAL = auto()
    MAGIC = auto()
    HEALING = auto()
    SUPPORT = auto()
    PASSIVE = auto()


@dataclass
class LearnCondition:
    """Condition for learning a skill."""
    min_level: int = 1
    required_skills: list[str] = field(default_factory=list)
    required_class: Optional[CharacterClass] = None
    required_item: Optional[str] = None


@dataclass
class SkillDefinition:
    """Complete definition of a skill."""
    id: str
    name: str
    description: str = ""
    category: SkillCategory = SkillCategory.PHYSICAL

    # Learning
    learn_condition: LearnCondition = field(default_factory=LearnCondition)
    is_default: bool = False

    # Battle data reference
    battle_skill_id: str = ""


@dataclass
class SkillTreeNode:
    """A node in a skill tree."""
    skill_id: str
    x: int = 0
    y: int = 0
    connections: list[str] = field(default_factory=list)


@dataclass
class SkillTree:
    """A tree of learnable skills."""
    id: str
    name: str
    character_class: Optional[CharacterClass] = None
    nodes: dict[str, SkillTreeNode] = field(default_factory=dict)


class SkillManager:
    """
    Manages skill definitions and learning.
    """

    def __init__(self, data_path: str = "game/data/database"):
        self.data_path = Path(data_path)
        self._skills: dict[str, SkillDefinition] = {}
        self._skill_trees: dict[str, SkillTree] = {}

    def load_skills(self, filename: str = "skills.json") -> None:
        """Load skill definitions from JSON."""
        path = self.data_path / filename
        if not path.exists():
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for skill_data in data.get('skills', []):
            skill = SkillDefinition(
                id=skill_data['id'],
                name=skill_data['name'],
                description=skill_data.get('description', ''),
                category=SkillCategory[skill_data.get('category', 'PHYSICAL').upper()],
                is_default=skill_data.get('is_default', False),
                battle_skill_id=skill_data.get('battle_skill_id', skill_data['id']),
            )

            # Parse learn condition
            if 'learn' in skill_data:
                learn = skill_data['learn']
                skill.learn_condition = LearnCondition(
                    min_level=learn.get('level', 1),
                    required_skills=learn.get('skills', []),
                )

            self._skills[skill.id] = skill

    def load_skill_trees(self, filename: str = "skill_trees.json") -> None:
        """Load skill trees from JSON."""
        path = self.data_path / filename
        if not path.exists():
            return

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for tree_data in data.get('trees', []):
            tree = SkillTree(
                id=tree_data['id'],
                name=tree_data['name'],
            )

            for node_data in tree_data.get('nodes', []):
                node = SkillTreeNode(
                    skill_id=node_data['skill_id'],
                    x=node_data.get('x', 0),
                    y=node_data.get('y', 0),
                    connections=node_data.get('connections', []),
                )
                tree.nodes[node.skill_id] = node

            self._skill_trees[tree.id] = tree

    def get_skill(self, skill_id: str) -> Optional[SkillDefinition]:
        """Get a skill definition."""
        return self._skills.get(skill_id)

    def get_skill_tree(self, tree_id: str) -> Optional[SkillTree]:
        """Get a skill tree."""
        return self._skill_trees.get(tree_id)

    def can_learn_skill(
        self,
        skill_id: str,
        level: int,
        known_skills: set[str],
        character_class: Optional[CharacterClass] = None,
    ) -> bool:
        """Check if a skill can be learned."""
        skill = self._skills.get(skill_id)
        if not skill:
            return False

        condition = skill.learn_condition

        # Check level
        if level < condition.min_level:
            return False

        # Check required skills
        for req_skill in condition.required_skills:
            if req_skill not in known_skills:
                return False

        # Check class
        if condition.required_class and condition.required_class != character_class:
            return False

        return True

    def get_default_skills(
        self,
        character_class: Optional[CharacterClass] = None,
    ) -> list[str]:
        """Get default skills for a class."""
        defaults = []
        for skill in self._skills.values():
            if skill.is_default:
                if skill.learn_condition.required_class is None or \
                   skill.learn_condition.required_class == character_class:
                    defaults.append(skill.id)
        return defaults

    def get_learnable_skills(
        self,
        level: int,
        known_skills: set[str],
        character_class: Optional[CharacterClass] = None,
    ) -> list[str]:
        """Get all skills that can be learned."""
        learnable = []
        for skill_id in self._skills:
            if skill_id not in known_skills:
                if self.can_learn_skill(skill_id, level, known_skills, character_class):
                    learnable.append(skill_id)
        return learnable
