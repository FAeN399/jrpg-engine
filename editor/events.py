"""
Editor-specific events.

Events for editor operations like entity selection,
component modifications, etc.
"""

from __future__ import annotations

from enum import Enum, auto


class EditorEvent(Enum):
    """Editor-specific events."""

    # Selection events
    ENTITY_SELECTED = auto()
    ENTITY_DESELECTED = auto()
    SELECTION_CLEARED = auto()

    # Entity editing events
    ENTITY_RENAMED = auto()
    ENTITY_CREATED_BY_USER = auto()
    ENTITY_DELETED_BY_USER = auto()

    # Component editing events
    COMPONENT_MODIFIED = auto()
    COMPONENT_ADDED_BY_USER = auto()
    COMPONENT_REMOVED_BY_USER = auto()

    # Project events
    PROJECT_LOADED = auto()
    PROJECT_SAVED = auto()
    PROJECT_MODIFIED = auto()
