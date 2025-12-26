"""
Component base class for data-only components.

Components are pure data containers with NO logic.
All logic lives in Systems. This separation makes:
- AI code generation more reliable
- Serialization trivial
- Testing easier

Usage:
    from pydantic import BaseModel

    class Health(Component):
        current: int
        max: int

    class Transform(Component):
        x: float = 0.0
        y: float = 0.0
        rotation: float = 0.0
        scale_x: float = 1.0
        scale_y: float = 1.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from engine.core.entity import Entity


class Component(BaseModel):
    """
    Base class for all components.

    Components are data-only containers using Pydantic for:
    - Automatic validation
    - JSON serialization
    - Type hints
    - Default values

    IMPORTANT: Do NOT add methods that modify state.
    All logic belongs in Systems.
    """

    model_config = ConfigDict(
        # Allow arbitrary types (for references)
        arbitrary_types_allowed=True,
        # Validate on assignment
        validate_assignment=True,
        # Allow extra fields for flexibility
        extra='forbid',
    )

    # Class variable: component type name (used for serialization)
    _type_name: ClassVar[str] = ""

    # Reference to owning entity (set by entity when attached)
    # Using Any to avoid circular import issues
    _entity_id: int | None = None

    @classmethod
    def get_type_name(cls) -> str:
        """Get the component type name for serialization."""
        return cls._type_name or cls.__name__

    def model_post_init(self, __context) -> None:
        """Called after model initialization."""
        pass

    def clone(self) -> Component:
        """Create a deep copy of this component."""
        return self.model_copy(deep=True)


# Registry of component types for deserialization
_component_registry: dict[str, type[Component]] = {}


def register_component(cls: type[Component]) -> type[Component]:
    """
    Decorator to register a component type.

    Usage:
        @register_component
        class Health(Component):
            current: int
            max: int
    """
    type_name = cls.get_type_name()
    _component_registry[type_name] = cls
    return cls


def get_component_type(type_name: str) -> type[Component] | None:
    """Get component class by type name."""
    return _component_registry.get(type_name)


def get_all_component_types() -> dict[str, type[Component]]:
    """Get all registered component types."""
    return _component_registry.copy()
