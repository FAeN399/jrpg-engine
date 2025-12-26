"""
UI System for JRPG-style menus, dialogs, and HUD elements.

This module provides a complete UI framework designed for:
- Gamepad/keyboard navigation (primary)
- Mouse support (secondary)
- Layer-based rendering
- Theme customization

Quick Start:
    from engine.ui import UIManager, Button, Container

    ui = UIManager(event_bus, input_handler)

    menu = Container()
    menu.add_child(Button("New Game", on_click=start_game))
    menu.add_child(Button("Continue", on_click=load_game))
    menu.add_child(Button("Quit", on_click=quit_game))

    ui.push_modal(menu)

Architecture:
    - Widget: Base class for all UI elements
    - Container: Widget that holds children
    - UIManager: Central hub for UI system
    - UIRenderer: Drawing primitives and text
    - Theme: Visual styling system
"""

# Core
from engine.ui.widget import Widget, Rect, Padding, Margin
from engine.ui.container import Container
from engine.ui.manager import UIManager, UILayer, UIEvent
from engine.ui.renderer import UIRenderer, FontConfig
from engine.ui.focus import FocusManager, FocusDirection, FocusContext, FocusGroup
from engine.ui.theme import (
    Theme,
    ColorPalette,
    FontSettings,
    Spacing,
    AnimationSettings,
    DEFAULT_THEME,
    DARK_THEME,
    LIGHT_THEME,
    JRPG_CLASSIC_THEME,
    get_theme,
    register_theme,
)

# Widgets
from engine.ui.widgets import (
    Label,
    Image,
    Button,
    Panel,
    SelectionList,
    ListItem,
    SelectableGrid,
    GridCell,
    ProgressBar,
    TextBox,
    InputField,
)

# Layouts
from engine.ui.layouts import (
    Layout,
    Alignment,
    VBoxLayout,
    HBoxLayout,
    GridLayout,
    AnchorLayout,
    Anchor,
)

# Presets
from engine.ui.presets import (
    DialogBox,
    ChoiceMenu,
    MainMenu,
    PauseMenu,
    InventoryScreen,
    EquipmentScreen,
    StatusScreen,
    BattleHUD,
    ShopScreen,
)

__all__ = [
    # Core widgets
    "Widget",
    "Container",
    "Rect",
    "Padding",
    "Margin",

    # Manager
    "UIManager",
    "UILayer",
    "UIEvent",

    # Renderer
    "UIRenderer",
    "FontConfig",

    # Focus
    "FocusManager",
    "FocusDirection",
    "FocusContext",
    "FocusGroup",

    # Theme
    "Theme",
    "ColorPalette",
    "FontSettings",
    "Spacing",
    "AnimationSettings",
    "DEFAULT_THEME",
    "DARK_THEME",
    "LIGHT_THEME",
    "JRPG_CLASSIC_THEME",
    "get_theme",
    "register_theme",

    # Widgets
    "Label",
    "Image",
    "Button",
    "Panel",
    "SelectionList",
    "ListItem",
    "SelectableGrid",
    "GridCell",
    "ProgressBar",
    "TextBox",
    "InputField",

    # Layouts
    "Layout",
    "Alignment",
    "VBoxLayout",
    "HBoxLayout",
    "GridLayout",
    "AnchorLayout",
    "Anchor",

    # Presets
    "DialogBox",
    "ChoiceMenu",
    "MainMenu",
    "PauseMenu",
    "InventoryScreen",
    "EquipmentScreen",
    "StatusScreen",
    "BattleHUD",
    "ShopScreen",
]
