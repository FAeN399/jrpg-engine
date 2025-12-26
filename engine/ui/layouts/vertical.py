"""
Vertical box layout - stacks children vertically.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from engine.ui.layouts.layout import Layout, Alignment

if TYPE_CHECKING:
    pass


class VBoxLayout(Layout):
    """
    Vertical box layout.

    Stacks children from top to bottom with optional spacing.

    Usage:
        layout = VBoxLayout()
        layout.add_child(Button("Option 1"))
        layout.add_child(Button("Option 2"))
        layout.add_child(Button("Option 3"))
    """

    def __init__(self):
        super().__init__()
        self.spacing = 8

    def layout(self) -> None:
        """Position children vertically."""
        if not self.children:
            if self.fit_content:
                self.rect.width = self.padding.horizontal
                self.rect.height = self.padding.vertical
            return

        # Calculate content area
        content_x = self.padding.left
        content_y = self.padding.top
        content_width = self.rect.width - self.padding.horizontal
        content_height = self.rect.height - self.padding.vertical

        # Calculate total height needed
        total_height = 0
        visible_children = [c for c in self.children if c.visible]

        for i, child in enumerate(visible_children):
            _, h = self._get_child_size(child)
            total_height += h
            if i < len(visible_children) - 1:
                total_height += self.spacing

        # Calculate starting Y based on alignment
        if self.align == Alignment.START:
            current_y = content_y
        elif self.align == Alignment.CENTER:
            current_y = content_y + (content_height - total_height) / 2
        elif self.align == Alignment.END:
            current_y = content_y + content_height - total_height
        else:  # STRETCH - distribute evenly
            current_y = content_y

        # Position children
        for i, child in enumerate(visible_children):
            # Apply cross-axis alignment (horizontal)
            offset_x = self._apply_cross_alignment(child, content_width, is_vertical=True)
            child.rect.x = content_x + offset_x

            # Position on main axis
            child.rect.y = current_y + child.margin.top

            # Move to next position
            current_y += child.rect.height + child.margin.top + child.margin.bottom

            if i < len(visible_children) - 1:
                current_y += self.spacing

            # Trigger child layout
            child.layout()

        # Fit content if enabled
        if self.fit_content:
            max_width = 0
            for child in visible_children:
                w, _ = self._get_child_size(child)
                max_width = max(max_width, w)

            self.rect.width = max_width + self.padding.horizontal
            self.rect.height = total_height + self.padding.vertical

    def get_preferred_size(self) -> Tuple[float, float]:
        """Calculate preferred size based on children."""
        if not self.children:
            return (self.padding.horizontal, self.padding.vertical)

        total_height = 0
        max_width = 0
        visible_children = [c for c in self.children if c.visible]

        for i, child in enumerate(visible_children):
            w, h = self._get_child_size(child)
            max_width = max(max_width, w)
            total_height += h

            if i < len(visible_children) - 1:
                total_height += self.spacing

        return (
            max_width + self.padding.horizontal,
            total_height + self.padding.vertical
        )
