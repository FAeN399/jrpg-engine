"""
Entity class - a container for components.

Entities are lightweight containers that hold components.
They have no behavior themselves - all logic is in Systems.

Usage:
    entity = Entity()
    entity.add(Transform(x=100, y=200))
    entity.add(Health(current=100, max=100))

    transform = entity.get(Transform)
    if entity.has(Health):
        health = entity.get(Health)
"""

from __future__ import annotations

from typing import TypeVar, Iterator, Any
import itertools

from engine.core.component import Component


# Type variable for component types
C = TypeVar('C', bound=Component)


class Entity:
    """
    A container for components.

    Entities are identified by unique IDs and contain
    a collection of components. They have no behavior -
    all logic is handled by Systems.
    """

    # Global entity ID counter
    _id_counter = itertools.count(1)

    def __init__(self, name: str = ""):
        self._id = next(Entity._id_counter)
        self._name = name or f"Entity_{self._id}"
        self._components: dict[type[Component], Component] = {}
        self._tags: set[str] = set()
        self._active = True
        self._world = None  # Set by World when added

    @property
    def id(self) -> int:
        """Unique entity identifier."""
        return self._id

    @property
    def name(self) -> str:
        """Entity name (for debugging)."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def active(self) -> bool:
        """Whether entity is active (processed by systems)."""
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        self._active = value

    @property
    def world(self) -> Any:
        """The World this entity belongs to."""
        return self._world

    def add(self, component: C) -> C:
        """
        Add a component to this entity.

        Args:
            component: The component to add

        Returns:
            The added component (for chaining)

        Raises:
            ValueError: If entity already has this component type
        """
        comp_type = type(component)

        if comp_type in self._components:
            raise ValueError(
                f"Entity {self._name} already has component {comp_type.__name__}"
            )

        component._entity_id = self._id
        self._components[comp_type] = component

        # Notify world if attached
        if self._world:
            self._world._on_component_added(self, component)

        return component

    def remove(self, component_type: type[C]) -> C | None:
        """
        Remove a component from this entity.

        Args:
            component_type: The component class to remove

        Returns:
            The removed component, or None if not found
        """
        component = self._components.pop(component_type, None)

        if component:
            component._entity_id = None

            # Notify world if attached
            if self._world:
                self._world._on_component_removed(self, component)

        return component

    def get(self, component_type: type[C]) -> C:
        """
        Get a component by type.

        Args:
            component_type: The component class

        Returns:
            The component

        Raises:
            KeyError: If component not found
        """
        if component_type not in self._components:
            raise KeyError(
                f"Entity {self._name} does not have component {component_type.__name__}"
            )
        return self._components[component_type]  # type: ignore

    def try_get(self, component_type: type[C]) -> C | None:
        """
        Try to get a component by type.

        Args:
            component_type: The component class

        Returns:
            The component, or None if not found
        """
        return self._components.get(component_type)  # type: ignore

    def has(self, *component_types: type[Component]) -> bool:
        """
        Check if entity has all specified component types.

        Args:
            *component_types: Component classes to check

        Returns:
            True if entity has all components
        """
        return all(ct in self._components for ct in component_types)

    def has_any(self, *component_types: type[Component]) -> bool:
        """
        Check if entity has any of the specified component types.

        Args:
            *component_types: Component classes to check

        Returns:
            True if entity has at least one component
        """
        return any(ct in self._components for ct in component_types)

    @property
    def components(self) -> Iterator[Component]:
        """Iterate over all components."""
        return iter(self._components.values())

    @property
    def component_types(self) -> set[type[Component]]:
        """Get set of component types on this entity."""
        return set(self._components.keys())

    # Tag management

    def add_tag(self, tag: str) -> None:
        """Add a tag to this entity."""
        self._tags.add(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag from this entity."""
        self._tags.discard(tag)

    def has_tag(self, tag: str) -> bool:
        """Check if entity has a tag."""
        return tag in self._tags

    @property
    def tags(self) -> frozenset[str]:
        """Get all tags."""
        return frozenset(self._tags)

    # Serialization

    def to_dict(self) -> dict:
        """Serialize entity to dictionary."""
        return {
            "id": self._id,
            "name": self._name,
            "active": self._active,
            "tags": list(self._tags),
            "components": {
                comp_type.__name__: comp.model_dump()
                for comp_type, comp in self._components.items()
            }
        }

    def __repr__(self) -> str:
        components = ", ".join(c.__name__ for c in self._components.keys())
        return f"Entity({self._name}, id={self._id}, components=[{components}])"

    def __hash__(self) -> int:
        return hash(self._id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Entity):
            return self._id == other._id
        return False
