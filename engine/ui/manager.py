"""
UI Manager - Central hub for the UI system.

Manages widgets, focus, input routing, and rendering layers.
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, List, Optional, Dict

from engine.ui.focus import FocusManager, FocusDirection
from engine.ui.theme import Theme, DEFAULT_THEME

if TYPE_CHECKING:
    from engine.core.events import EventBus
    from engine.input.handler import InputHandler
    from engine.ui.widget import Widget
    from engine.ui.container import Container
    from engine.ui.renderer import UIRenderer


class UILayer(Enum):
    """UI rendering layers (lower = rendered first)."""
    GAME_HUD = 0      # Always visible during gameplay
    MENU = 10         # Pause menu, inventory, etc.
    DIALOG = 20       # Dialog boxes
    POPUP = 30        # Confirmations, tooltips
    SYSTEM = 40       # Loading screens, fade overlays


class UIEvent(Enum):
    """UI-specific events."""
    MENU_OPENED = auto()
    MENU_CLOSED = auto()
    DIALOG_STARTED = auto()
    DIALOG_ENDED = auto()
    WIDGET_FOCUSED = auto()
    WIDGET_UNFOCUSED = auto()
    BUTTON_CLICKED = auto()
    SELECTION_CHANGED = auto()


class UIManager:
    """
    Central UI management system.

    Responsibilities:
    - Widget tree management
    - Layer-based rendering
    - Focus and navigation
    - Input routing (UI vs game)
    - Modal dialog stack
    - Theme management
    """

    def __init__(
        self,
        event_bus: Optional['EventBus'] = None,
        input_handler: Optional['InputHandler'] = None,
    ):
        self.event_bus = event_bus
        self.input_handler = input_handler

        # Layer management
        self.layers: Dict[UILayer, List[Widget]] = {
            layer: [] for layer in UILayer
        }

        # Modal dialog stack
        self.modal_stack: List[Container] = []

        # Focus management
        self.focus_manager = FocusManager()

        # Theme
        self._theme = DEFAULT_THEME

        # State
        self._captures_input = False
        self._mouse_over: Optional[Widget] = None

    @property
    def theme(self) -> Theme:
        """Get current theme."""
        return self._theme

    @theme.setter
    def theme(self, value: Theme) -> None:
        """Set theme for all widgets."""
        self._theme = value

    @property
    def captures_input(self) -> bool:
        """True if UI is blocking game input."""
        return self._captures_input or len(self.modal_stack) > 0

    @captures_input.setter
    def captures_input(self, value: bool) -> None:
        """Set whether UI captures input."""
        self._captures_input = value

    # Widget management

    def add_widget(
        self,
        widget: 'Widget',
        layer: UILayer = UILayer.GAME_HUD,
    ) -> None:
        """
        Add a widget to a layer.

        Args:
            widget: Widget to add
            layer: Rendering layer
        """
        widget.manager = self
        self.layers[layer].append(widget)

    def remove_widget(self, widget: 'Widget') -> bool:
        """
        Remove a widget from all layers.

        Returns:
            True if widget was found and removed
        """
        for layer_widgets in self.layers.values():
            if widget in layer_widgets:
                layer_widgets.remove(widget)
                widget.manager = None

                # Clear focus if this widget had it
                if self.focus_manager.focused == widget:
                    self.focus_manager.clear_focus()

                return True
        return False

    def clear_layer(self, layer: UILayer) -> None:
        """Remove all widgets from a layer."""
        for widget in self.layers[layer]:
            widget.manager = None
        self.layers[layer].clear()

    def clear_all(self) -> None:
        """Remove all widgets from all layers."""
        for layer in UILayer:
            self.clear_layer(layer)
        self.modal_stack.clear()
        self.focus_manager.clear_focus()

    def get_widgets(self, layer: Optional[UILayer] = None) -> List['Widget']:
        """Get widgets from a layer or all layers."""
        if layer is not None:
            return self.layers[layer].copy()

        result = []
        for layer_widgets in self.layers.values():
            result.extend(layer_widgets)
        return result

    def find_widget(self, tag: str) -> Optional['Widget']:
        """Find a widget by tag across all layers."""
        for layer_widgets in self.layers.values():
            for widget in layer_widgets:
                found = widget.find_by_tag(tag)
                if found:
                    return found
        return None

    # Modal dialogs

    def push_modal(
        self,
        container: 'Container',
        layer: UILayer = UILayer.MENU,
    ) -> None:
        """
        Push a modal dialog.

        Modal dialogs block game input and capture focus.

        Args:
            container: The modal container
            layer: Layer to add the modal to
        """
        self.modal_stack.append(container)
        self.add_widget(container, layer)

        # Push focus context
        self.focus_manager.push_context(container, trap_focus=True)

        # Emit event
        if self.event_bus:
            self.event_bus.publish(UIEvent.MENU_OPENED, container=container)

    def pop_modal(self) -> Optional['Container']:
        """
        Pop the top modal dialog.

        Returns:
            The popped container, or None if no modals
        """
        if not self.modal_stack:
            return None

        container = self.modal_stack.pop()
        self.remove_widget(container)

        # Pop focus context
        self.focus_manager.pop_context()

        # Emit event
        if self.event_bus:
            self.event_bus.publish(UIEvent.MENU_CLOSED, container=container)

        return container

    def pop_all_modals(self) -> None:
        """Pop all modal dialogs."""
        while self.modal_stack:
            self.pop_modal()

    @property
    def current_modal(self) -> Optional['Container']:
        """Get the current modal dialog."""
        return self.modal_stack[-1] if self.modal_stack else None

    # Focus

    def set_focus(self, widget: Optional['Widget']) -> bool:
        """Set focus to a widget."""
        return self.focus_manager.set_focus(widget)

    @property
    def focused_widget(self) -> Optional['Widget']:
        """Get currently focused widget."""
        return self.focus_manager.focused

    # Input handling

    def handle_input(self) -> bool:
        """
        Process input for the UI system.

        Should be called each frame before game input handling.

        Returns:
            True if input was consumed by UI
        """
        if not self.input_handler:
            return False

        # If no modals and not capturing input, let game handle it
        if not self.captures_input:
            return False

        # Get focused widget
        focused = self.focus_manager.focused
        if not focused:
            # Try to focus something in current modal
            if self.current_modal:
                self.current_modal.focus_first()
                focused = self.focus_manager.focused

            if not focused:
                return False

        # Import here to avoid circular import
        from engine.core.actions import Action

        # Navigation
        if self.input_handler.is_action_just_pressed(Action.MENU_UP):
            if focused.navigate(-1, 0):
                return True

        if self.input_handler.is_action_just_pressed(Action.MENU_DOWN):
            if focused.navigate(1, 0):
                return True

        if self.input_handler.is_action_just_pressed(Action.MENU_LEFT):
            if focused.navigate(0, -1):
                return True

        if self.input_handler.is_action_just_pressed(Action.MENU_RIGHT):
            if focused.navigate(0, 1):
                return True

        # Confirm/Cancel
        if self.input_handler.is_action_just_pressed(Action.CONFIRM):
            if focused.on_confirm():
                return True

        if self.input_handler.is_action_just_pressed(Action.CANCEL):
            if focused.on_cancel():
                return True
            # Default cancel: pop modal
            if self.modal_stack:
                self.pop_modal()
                return True

        return False

    def handle_mouse(self, x: int, y: int, buttons: tuple[bool, bool, bool]) -> bool:
        """
        Process mouse input.

        Args:
            x, y: Mouse position
            buttons: (left, middle, right) button states

        Returns:
            True if mouse was over a UI widget
        """
        if not self.captures_input:
            return False

        # Find widget under mouse (top layer first)
        widget = self._find_widget_at(x, y)

        # Handle hover state changes
        if widget != self._mouse_over:
            if self._mouse_over:
                self._mouse_over.on_mouse_exit()
            if widget:
                widget.on_mouse_enter()
            self._mouse_over = widget

        # Handle clicks
        if widget and buttons[0]:  # Left click
            widget.on_mouse_down(x, y, 1)
            # Focus on click
            if widget.focusable:
                self.set_focus(widget)
            return True

        return widget is not None

    def _find_widget_at(self, x: float, y: float) -> Optional['Widget']:
        """Find topmost widget at screen position."""
        # Check layers in reverse order (top first)
        for layer in reversed(UILayer):
            for widget in reversed(self.layers[layer]):
                if widget.visible:
                    hit = self._hit_test(widget, x, y)
                    if hit:
                        return hit
        return None

    def _hit_test(self, widget: 'Widget', x: float, y: float) -> Optional['Widget']:
        """Recursive hit test."""
        rect = widget.absolute_rect
        if not rect.contains(x, y):
            return None

        # Check children first (they're on top)
        from engine.ui.container import Container
        if isinstance(widget, Container):
            for child in reversed(widget.children):
                if child.visible:
                    hit = self._hit_test(child, x, y)
                    if hit:
                        return hit

        return widget

    # Lifecycle

    def update(self, dt: float) -> None:
        """Update all visible widgets."""
        for layer in UILayer:
            for widget in self.layers[layer]:
                if widget.visible:
                    widget.update(dt)

    def render(self, renderer: 'UIRenderer') -> None:
        """Render all visible widgets by layer."""
        for layer in UILayer:
            for widget in self.layers[layer]:
                if widget.visible:
                    widget.render(renderer)

    # Utility

    def show_dialog(
        self,
        text: str,
        speaker: Optional[str] = None,
        on_complete: Optional[callable] = None,
    ) -> 'Widget':
        """
        Convenience method to show a dialog box.

        Returns the created dialog widget.
        """
        # Import here to avoid circular import at module level
        from engine.ui.presets.dialog_box import DialogBox

        dialog = DialogBox()
        dialog.set_text(text, speaker=speaker)
        if on_complete:
            dialog.on_complete = on_complete

        self.push_modal(dialog, UILayer.DIALOG)
        return dialog

    def show_choice(
        self,
        prompt: str,
        choices: List[str],
        on_select: Optional[callable] = None,
    ) -> 'Widget':
        """
        Convenience method to show a choice menu.

        Returns the created choice widget.
        """
        from engine.ui.presets.choice_menu import ChoiceMenu

        menu = ChoiceMenu(prompt, choices)
        if on_select:
            menu.on_select = on_select

        self.push_modal(menu, UILayer.DIALOG)
        return menu
