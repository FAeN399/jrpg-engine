"""
Horizontal box layout - stacks children horizontally.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from engine.ui.layouts.layout import Layout, Alignment

if TYPE_CHECKING:
    pass


class HBoxLayout(Layout):
    """
    Horizontal box layout.

    Stacks children from left to right with optional spacing.

    Usage:
        layout = HBoxLayout()
        layout.add_child(Button("Yes"))
        layout.add_child(Button("No"))
    """

    def __init__(self):
        super().__init__()
        self.spacing = 8

    def layout(self) -> None:
        """Position children horizontally."""
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

        # Calculate total width needed
        total_width = 0
        visible_children = [c for c in self.children if c.visible]

        for i, child in enumerate(visible_children):
            w, _ = self._get_child_size(child)
            total_width += w
            if i < len(visible_children) - 1:
                total_width += self.spacing

        # Calculate starting X based on alignment
        if self.align == Alignment.START:
            current_x = content_x
        elif self.align == Alignment.CENTER:
            current_x = content_x + (content_width - total_width) / 2
        elif self.align == Alignment.END:
            current_x = content_x + content_width - total_width
        else:  # STRETCH - distribute evenly
            current_x = content_x

        # Position children
        for i, child in enumerate(visible_children):
            # Apply cross-axis alignment (vertical)
            offset_y = self._apply_cross_alignment(child, content_height, is_vertical=False)
            child.rect.y = content_y + offset_y

            # Position on main axis
            child.rect.x = current_x + child.margin.left

            # Move to next position
            current_x += child.rect.width + child.margin.left + child.margin.right

            if i < len(visible_children) - 1:
                current_x += self.spacing

            # Trigger child layout
            child.layout()

        # Fit content if enabled
        if self.fit_content:
            max_height = 0
            for child in visible_children:
                _, h = self._get_child_size(child)
                max_height = max(max_height, h)

            self.rect.width = total_width + self.padding.horizontal
            self.rect.height = max_height + self.padding.vertical

    def get_preferred_size(self) -> Tuple[float, float]:
        """Calculate preferred size based on children."""
        if not self.children:
            return (self.padding.horizontal, self.padding.vertical)

        total_width = 0
        max_height = 0
        visible_children = [c for c in self.children if c.visible]

        for i, child in enumerate(visible_children):
            w, h = self._get_child_size(child)
            max_height = max(max_height, h)
            total_width += w

            if i < len(visible_children) - 1:
                total_width += self.spacing

        return (
            total_width + self.padding.horizontal,
            max_height + self.padding.vertical
        )

    def navigate(self, row_delta: int, col_delta: int) -> bool:
        """Handle horizontal navigation."""
        # For horizontal layout, use col_delta for navigation
        if col_delta != 0:
            if col_delta > 0:
                return self.focus_next()
            else:
                return self.focus_prev()
        return False
