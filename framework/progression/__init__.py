"""
Progression module - stats, skills, quests.

Provides:
- Skill definitions and learning
- Skill trees
- Quest tracking and objectives
"""

from framework.progression.skills import (
    SkillManager,
    SkillDefinition,
    SkillCategory,
    SkillTree,
    SkillTreeNode,
    LearnCondition,
)
from framework.progression.quests import (
    QuestManager,
    Quest,
    QuestObjective,
    QuestReward,
    QuestStatus,
    ObjectiveType,
)

__all__ = [
    # Skills
    "SkillManager",
    "SkillDefinition",
    "SkillCategory",
    "SkillTree",
    "SkillTreeNode",
    "LearnCondition",
    # Quests
    "QuestManager",
    "Quest",
    "QuestObjective",
    "QuestReward",
    "QuestStatus",
    "ObjectiveType",
]
