"""
Pre-built UI screens for common JRPG patterns.

Basic presets:
- DialogBox: RPG-style dialog with typewriter effect
- ChoiceMenu: Yes/No or multiple choice selection
- MainMenu: Title screen menu
- PauseMenu: In-game pause menu

Game screens:
- InventoryScreen: Item management
- EquipmentScreen: Equipment slots
- StatusScreen: Character status display
- BattleHUD: Battle UI overlay
- ShopScreen: Buy/sell interface
"""

from engine.ui.presets.dialog_box import DialogBox
from engine.ui.presets.choice_menu import ChoiceMenu
from engine.ui.presets.main_menu import MainMenu
from engine.ui.presets.pause_menu import PauseMenu
from engine.ui.presets.inventory_screen import InventoryScreen
from engine.ui.presets.equipment_screen import EquipmentScreen
from engine.ui.presets.status_screen import StatusScreen
from engine.ui.presets.battle_hud import BattleHUD
from engine.ui.presets.shop_screen import ShopScreen

__all__ = [
    # Basic
    "DialogBox",
    "ChoiceMenu",
    "MainMenu",
    "PauseMenu",

    # Game screens
    "InventoryScreen",
    "EquipmentScreen",
    "StatusScreen",
    "BattleHUD",
    "ShopScreen",
]
