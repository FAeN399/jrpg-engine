"""
Anchor layout - positions children relative to anchor points.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Flag, auto
from typing import TYPE_CHECKING, Dict, Tuple, Optional

from engine.ui.container import Container

if TYPE_CHECKING:
    from engine.ui.widget import Widget
    from engine.ui.renderer import UIRenderer


class Anchor(Flag):
    """Anchor points for positioning."""
    NONE = 0
    LEFT = auto()
    RIGHT = auto()
    TOP = auto()
    BOTTOM = auto()
    CENTER_H = auto()  # Horizontal center
    CENTER_V = auto()  # Vertical center

    # Common combinations
    TOP_LEFT = TOP | LEFT
    TOP_RIGHT = TOP | RIGHT
    TOP_CENTER = TOP | CENTER_H
    BOTTOM_LEFT = BOTTOM | LEFT
    BOTTOM_RIGHT = BOTTOM | RIGHT
    BOTTOM_CENTER = BOTTOM | CENTER_H
    CENTER_LEFT = CENTER_V | LEFT
    CENTER_RIGHT = CENTER_V | RIGHT
    CENTER = CENTER_H | CENTER_V
    FILL = LEFT | RIGHT | TOP | BOTTOM


@dataclass
class AnchorConstraint:
    """Constraint for a widget in anchor layout."""
    anchor: Anchor = Anchor.TOP_LEFT
    margin_left: float = 0
    margin_right: float = 0
    margin_top: float = 0
    margin_bottom: float = 0


class AnchorLayout(Container):
    """
    Anchor-based layout.

    Positions children relative to edges or center of the container.
    Useful for HUD elements and screen overlays.

    Usage:
        layout = AnchorLayout()

        # Position button at bottom-center
        layout.add_child(Button("OK"))
        layout.set_anchor(button, Anchor.BOTTOM_CENTER, margin_bottom=20)

        # Position label at top-left
        layout.add_child(Label("Score: 0"))
        layout.set_anchor(label, Anchor.TOP_LEFT, margin_left=10, margin_top=10)
    """

    def __init__(self):
        super().__init__()
        self._constraints: Dict[int, AnchorConstraint] = {}

    def add_child(self, widget: 'Widget') -> 'AnchorLayout':
        """Add child with default anchor."""
        super().add_child(widget)
        self._constraints[id(widget)] = AnchorConstraint()
        return self

    def remove_child(self, widget: 'Widget') -> bool:
        """Remove child and its constraint."""
        result = super().remove_child(widget)
        if result and id(widget) in self._constraints:
            del self._constraints[id(widget)]
        return result

    def clear_children(self) -> None:
        """Clear all children and constraints."""
        super().clear_children()
        self._constraints.clear()

    def set_anchor(
        self,
        widget: 'Widget',
        anchor: Anchor,
        margin_left: float = 0,
        margin_right: float = 0,
        margin_top: float = 0,
        margin_bottom: float = 0,
    ) -> 'AnchorLayout':
        """
        Set anchor for a child widget.

        Args:
            widget: The child widget
            anchor: Anchor point(s)
            margin_*: Margins from edges
        """
        self._constraints[id(widget)] = AnchorConstraint(
            anchor=anchor,
            margin_left=margin_left,
            margin_right=margin_right,
            margin_top=margin_top,
            margin_bottom=margin_bottom,
        )
        self.layout()
        return self

    def get_constraint(self, widget: 'Widget') -> Optional[AnchorConstraint]:
        """Get constraint for a widget."""
        return self._constraints.get(id(widget))

    def layout(self) -> None:
        """Position children based on anchors."""
        content_width = self.rect.width - self.padding.horizontal
        content_height = self.rect.height - self.padding.vertical
        content_x = self.padding.left
        content_y = self.padding.top

        for child in self.children:
            if not child.visible:
                continue

            constraint = self._constraints.get(id(child))
            if not constraint:
                continue

            anchor = constraint.anchor
            x, y = 0.0, 0.0
            w = child.rect.width
            h = child.rect.height

            # Horizontal positioning
            if Anchor.LEFT in anchor and Anchor.RIGHT in anchor:
                # Fill horizontally
                x = content_x + constraint.margin_left
                w = content_width - constraint.margin_left - constraint.margin_right
                child.rect.width = w
            elif Anchor.LEFT in anchor:
                x = content_x + constraint.margin_left
            elif Anchor.RIGHT in anchor:
                x = content_x + content_width - w - constraint.margin_right
            elif Anchor.CENTER_H in anchor:
                x = content_x + (content_width - w) / 2

            # Vertical positioning
            if Anchor.TOP in anchor and Anchor.BOTTOM in anchor:
                # Fill vertically
                y = content_y + constraint.margin_top
                h = content_height - constraint.margin_top - constraint.margin_bottom
                child.rect.height = h
            elif Anchor.TOP in anchor:
                y = content_y + constraint.margin_top
            elif Anchor.BOTTOM in anchor:
                y = content_y + content_height - h - constraint.margin_bottom
            elif Anchor.CENTER_V in anchor:
                y = content_y + (content_height - h) / 2

            child.rect.x = x
            child.rect.y = y
            child.layout()

    def render(self, renderer: 'UIRenderer') -> None:
        """Render children (no background by default)."""
        for child in self.children:
            if child.visible:
                child.render(renderer)

    def get_preferred_size(self) -> Tuple[float, float]:
        """Calculate minimum size to contain all children."""
        min_width = self.padding.horizontal
        min_height = self.padding.vertical

        for child in self.children:
            if not child.visible:
                continue

            constraint = self._constraints.get(id(child))
            if not constraint:
                continue

            # Calculate required size based on anchor
            anchor = constraint.anchor

            if Anchor.LEFT in anchor or Anchor.CENTER_H in anchor:
                required_w = constraint.margin_left + child.rect.width
                if Anchor.RIGHT in anchor:
                    required_w += constraint.margin_right
            elif Anchor.RIGHT in anchor:
                required_w = child.rect.width + constraint.margin_right
            else:
                required_w = child.rect.width

            if Anchor.TOP in anchor or Anchor.CENTER_V in anchor:
                required_h = constraint.margin_top + child.rect.height
                if Anchor.BOTTOM in anchor:
                    required_h += constraint.margin_bottom
            elif Anchor.BOTTOM in anchor:
                required_h = child.rect.height + constraint.margin_bottom
            else:
                required_h = child.rect.height

            min_width = max(min_width, required_w + self.padding.horizontal)
            min_height = max(min_height, required_h + self.padding.vertical)

        return (min_width, min_height)
