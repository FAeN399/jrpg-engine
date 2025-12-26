"""
UI Widgets collection.

Basic widgets:
- Label: Text display
- Image: Image/sprite display
- Button: Clickable/selectable button
- Panel: Background container

Advanced widgets:
- SelectionList: Scrollable selection list
- SelectableGrid: Grid of selectable items
- ProgressBar: HP/MP bars
- TextBox: Multi-line text with typewriter effect
- InputField: Text input for naming
"""

from engine.ui.widgets.label import Label
from engine.ui.widgets.image import Image
from engine.ui.widgets.button import Button
from engine.ui.widgets.panel import Panel
from engine.ui.widgets.selection_list import SelectionList, ListItem
from engine.ui.widgets.grid import SelectableGrid, GridCell
from engine.ui.widgets.progress_bar import ProgressBar
from engine.ui.widgets.text_box import TextBox
from engine.ui.widgets.input_field import InputField

__all__ = [
    # Basic
    "Label",
    "Image",
    "Button",
    "Panel",

    # Advanced
    "SelectionList",
    "ListItem",
    "SelectableGrid",
    "GridCell",
    "ProgressBar",
    "TextBox",
    "InputField",
]
