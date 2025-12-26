"""
Base layout class for automatic widget positioning.
"""

from __future__ import annotations

from abc import abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, Tuple

from engine.ui.container import Container

if TYPE_CHECKING:
    from engine.ui.widget import Widget


class Alignment(Enum):
    """Alignment options for layout children."""
    START = auto()    # Left/Top
    CENTER = auto()   # Center
    END = auto()      # Right/Bottom
    STRETCH = auto()  # Fill available space


class Layout(Container):
    """
    Base class for layout containers.

    Layouts automatically position their children according
    to a specific strategy (vertical, horizontal, grid, etc).
    """

    def __init__(self):
        super().__init__()

        # Spacing between children
        self.spacing: float = 8

        # Alignment of children
        self.align: Alignment = Alignment.START
        self.cross_align: Alignment = Alignment.START  # Perpendicular axis

        # Auto-size to content
        self.fit_content: bool = False

    @abstractmethod
    def layout(self) -> None:
        """Recalculate child positions."""
        pass

    def add_child(self, widget: 'Widget') -> 'Layout':
        """Add child and trigger layout."""
        super().add_child(widget)
        self.layout()
        return self

    def remove_child(self, widget: 'Widget') -> bool:
        """Remove child and trigger layout."""
        result = super().remove_child(widget)
        if result:
            self.layout()
        return result

    def clear_children(self) -> None:
        """Clear children and reset layout."""
        super().clear_children()
        self.layout()

    def set_spacing(self, spacing: float) -> 'Layout':
        """Set spacing between children (fluent)."""
        self.spacing = spacing
        self.layout()
        return self

    def set_align(self, align: Alignment) -> 'Layout':
        """Set main axis alignment (fluent)."""
        self.align = align
        self.layout()
        return self

    def set_cross_align(self, align: Alignment) -> 'Layout':
        """Set cross axis alignment (fluent)."""
        self.cross_align = align
        self.layout()
        return self

    def _get_child_size(self, child: 'Widget') -> Tuple[float, float]:
        """Get child's size including margins."""
        w = child.rect.width + child.margin.left + child.margin.right
        h = child.rect.height + child.margin.top + child.margin.bottom
        return (w, h)

    def _apply_cross_alignment(
        self,
        child: 'Widget',
        available: float,
        is_vertical: bool,
    ) -> float:
        """
        Calculate cross-axis position based on alignment.

        Returns offset from content area start.
        """
        if is_vertical:
            child_size = child.rect.width + child.margin.left + child.margin.right
        else:
            child_size = child.rect.height + child.margin.top + child.margin.bottom

        if self.cross_align == Alignment.START:
            return child.margin.left if is_vertical else child.margin.top
        elif self.cross_align == Alignment.CENTER:
            return (available - child_size) / 2 + (child.margin.left if is_vertical else child.margin.top)
        elif self.cross_align == Alignment.END:
            return available - child_size + (child.margin.left if is_vertical else child.margin.top)
        elif self.cross_align == Alignment.STRETCH:
            # Set child size to fill
            if is_vertical:
                child.rect.width = available - child.margin.left - child.margin.right
            else:
                child.rect.height = available - child.margin.top - child.margin.bottom
            return child.margin.left if is_vertical else child.margin.top

        return 0
