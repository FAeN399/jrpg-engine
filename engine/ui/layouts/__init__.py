"""
Layout containers for automatic widget positioning.

Layouts:
- VBoxLayout: Vertical stacking
- HBoxLayout: Horizontal stacking
- GridLayout: Grid arrangement
- AnchorLayout: Anchor-based positioning
"""

from engine.ui.layouts.layout import Layout, Alignment
from engine.ui.layouts.vertical import VBoxLayout
from engine.ui.layouts.horizontal import HBoxLayout
from engine.ui.layouts.grid import GridLayout
from engine.ui.layouts.anchor import AnchorLayout, Anchor

__all__ = [
    "Layout",
    "Alignment",
    "VBoxLayout",
    "HBoxLayout",
    "GridLayout",
    "AnchorLayout",
    "Anchor",
]
