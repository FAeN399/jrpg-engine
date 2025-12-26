"""
World container for entities and systems.

The World is the main container that holds:
- All entities
- All systems
- Component indices for fast queries

Each Scene typically has one World.

Usage:
    world = World()
    world.add_system(MovementSystem())
    world.add_system(RenderSystem())

    player = world.create_entity("Player")
    player.add(Transform(x=100, y=100))
    player.add(Velocity())

    # In game loop:
    world.update(dt)
    world.render(alpha)
"""

from __future__ import annotations

from typing import Iterator, TypeVar

from engine.core.entity import Entity
from engine.core.component import Component
from engine.core.system import System, RenderSystem
from engine.core.events import EventBus, EngineEvent


C = TypeVar('C', bound=Component)


class World:
    """
    Container for entities and systems.

    Provides:
    - Entity management (create, destroy, query)
    - System management (add, remove, update)
    - Component indices for fast entity queries
    - Event bus integration
    """

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus or EventBus()

        # Entity storage
        self._entities: dict[int, Entity] = {}
        self._entities_by_name: dict[str, Entity] = {}
        self._entities_to_destroy: list[int] = []

        # Component index: component_type -> set of entity IDs
        self._component_index: dict[type[Component], set[int]] = {}

        # Tag index: tag -> set of entity IDs
        self._tag_index: dict[str, set[int]] = {}

        # Systems (sorted by priority)
        self._systems: list[System] = []
        self._render_systems: list[RenderSystem] = []

    # Entity Management

    def create_entity(self, name: str = "") -> Entity:
        """
        Create a new entity in this world.

        Args:
            name: Optional entity name

        Returns:
            The new entity
        """
        entity = Entity(name)
        self._add_entity(entity)
        return entity

    def add_entity(self, entity: Entity) -> Entity:
        """
        Add an existing entity to this world.

        Args:
            entity: The entity to add

        Returns:
            The added entity
        """
        if entity.id in self._entities:
            raise ValueError(f"Entity {entity.id} already in world")

        self._add_entity(entity)
        return entity

    def _add_entity(self, entity: Entity) -> None:
        """Internal: add entity to world."""
        entity._world = self
        self._entities[entity.id] = entity

        if entity.name:
            self._entities_by_name[entity.name] = entity

        # Index existing components
        for component in entity.components:
            self._index_component(entity, type(component))

        # Index existing tags
        for tag in entity.tags:
            self._index_tag(entity, tag)

        # Publish event
        self.event_bus.publish(
            EngineEvent.ENTITY_CREATED,
            entity=entity
        )

    def destroy_entity(self, entity: Entity | int) -> None:
        """
        Mark an entity for destruction.

        Entity will be removed at the end of the current update.

        Args:
            entity: Entity or entity ID to destroy
        """
        entity_id = entity.id if isinstance(entity, Entity) else entity

        if entity_id not in self._entities:
            return

        if entity_id not in self._entities_to_destroy:
            self._entities_to_destroy.append(entity_id)

    def _process_destroyed_entities(self) -> None:
        """Internal: remove destroyed entities."""
        for entity_id in self._entities_to_destroy:
            if entity_id not in self._entities:
                continue

            entity = self._entities[entity_id]

            # Remove from indices
            for component in entity.components:
                self._unindex_component(entity, type(component))

            for tag in entity.tags:
                self._unindex_tag(entity, tag)

            # Remove from storage
            del self._entities[entity_id]
            if entity.name in self._entities_by_name:
                if self._entities_by_name[entity.name] is entity:
                    del self._entities_by_name[entity.name]

            entity._world = None

            # Publish event
            self.event_bus.publish(
                EngineEvent.ENTITY_DESTROYED,
                entity=entity
            )

        self._entities_to_destroy.clear()

    def get_entity(self, entity_id: int) -> Entity | None:
        """Get entity by ID."""
        return self._entities.get(entity_id)

    def get_entity_by_name(self, name: str) -> Entity | None:
        """Get entity by name."""
        return self._entities_by_name.get(name)

    @property
    def entities(self) -> Iterator[Entity]:
        """Iterate over all entities."""
        return iter(self._entities.values())

    @property
    def entity_count(self) -> int:
        """Get number of entities."""
        return len(self._entities)

    # Component indexing

    def _index_component(self, entity: Entity, component_type: type[Component]) -> None:
        """Add entity to component index."""
        if component_type not in self._component_index:
            self._component_index[component_type] = set()
        self._component_index[component_type].add(entity.id)

    def _unindex_component(self, entity: Entity, component_type: type[Component]) -> None:
        """Remove entity from component index."""
        if component_type in self._component_index:
            self._component_index[component_type].discard(entity.id)

    def _on_component_added(self, entity: Entity, component: Component) -> None:
        """Called when a component is added to an entity."""
        self._index_component(entity, type(component))
        self.event_bus.publish(
            EngineEvent.COMPONENT_ADDED,
            entity=entity,
            component=component
        )

    def _on_component_removed(self, entity: Entity, component: Component) -> None:
        """Called when a component is removed from an entity."""
        self._unindex_component(entity, type(component))
        self.event_bus.publish(
            EngineEvent.COMPONENT_REMOVED,
            entity=entity,
            component=component
        )

    # Tag indexing

    def _index_tag(self, entity: Entity, tag: str) -> None:
        """Add entity to tag index."""
        if tag not in self._tag_index:
            self._tag_index[tag] = set()
        self._tag_index[tag].add(entity.id)

    def _unindex_tag(self, entity: Entity, tag: str) -> None:
        """Remove entity from tag index."""
        if tag in self._tag_index:
            self._tag_index[tag].discard(entity.id)

    # Queries

    def get_entities_with(self, *component_types: type[Component]) -> Iterator[Entity]:
        """
        Get all entities that have ALL specified components.

        Args:
            *component_types: Component types to match

        Returns:
            Iterator of matching entities
        """
        if not component_types:
            return iter([])

        # Start with entities that have the first component
        first_type = component_types[0]
        if first_type not in self._component_index:
            return iter([])

        candidate_ids = self._component_index[first_type].copy()

        # Intersect with other component types
        for comp_type in component_types[1:]:
            if comp_type not in self._component_index:
                return iter([])
            candidate_ids &= self._component_index[comp_type]

        # Return matching entities
        for entity_id in candidate_ids:
            entity = self._entities.get(entity_id)
            if entity:
                yield entity

    def get_entities_with_tag(self, tag: str) -> Iterator[Entity]:
        """Get all entities with a specific tag."""
        if tag not in self._tag_index:
            return iter([])

        for entity_id in self._tag_index[tag]:
            entity = self._entities.get(entity_id)
            if entity:
                yield entity

    def get_entities_with_any(self, *component_types: type[Component]) -> Iterator[Entity]:
        """Get all entities that have ANY of the specified components."""
        seen: set[int] = set()

        for comp_type in component_types:
            if comp_type in self._component_index:
                for entity_id in self._component_index[comp_type]:
                    if entity_id not in seen:
                        seen.add(entity_id)
                        entity = self._entities.get(entity_id)
                        if entity:
                            yield entity

    # System Management

    def add_system(self, system: System) -> None:
        """
        Add a system to this world.

        Args:
            system: The system to add
        """
        if isinstance(system, RenderSystem):
            self._render_systems.append(system)
            self._render_systems.sort(key=lambda s: -s.priority)
        else:
            self._systems.append(system)
            self._systems.sort(key=lambda s: -s.priority)

        system.on_add(self)

    def remove_system(self, system: System) -> None:
        """Remove a system from this world."""
        if isinstance(system, RenderSystem):
            if system in self._render_systems:
                self._render_systems.remove(system)
                system.on_remove()
        else:
            if system in self._systems:
                self._systems.remove(system)
                system.on_remove()

    def get_system(self, system_type: type[System]) -> System | None:
        """Get a system by type."""
        for system in self._systems:
            if isinstance(system, system_type):
                return system
        for system in self._render_systems:
            if isinstance(system, system_type):
                return system
        return None

    # Update and Render

    def update(self, dt: float) -> None:
        """
        Update all systems.

        Args:
            dt: Delta time in seconds
        """
        # Update all logic systems
        for system in self._systems:
            if system.enabled:
                system.update(dt)

        # Process destroyed entities at end of update
        self._process_destroyed_entities()

    def render(self, alpha: float) -> None:
        """
        Render all render systems.

        Args:
            alpha: Interpolation factor
        """
        for system in self._render_systems:
            if system.enabled:
                system.render(alpha)

    def clear(self) -> None:
        """Remove all entities and systems."""
        # Destroy all entities
        for entity_id in list(self._entities.keys()):
            self.destroy_entity(entity_id)
        self._process_destroyed_entities()

        # Remove all systems
        for system in self._systems[:]:
            self.remove_system(system)
        for system in self._render_systems[:]:
            self.remove_system(system)

        # Clear indices
        self._component_index.clear()
        self._tag_index.clear()
