"""
Dialog system - renders dialog boxes with typewriter effect.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import json

from engine.core import System, World, Entity
from engine.core.actions import Action
from engine.core.events import EventBus, EngineEvent
from framework.components import DialogContext, DialogNode, DialogChoice, DialogState

if TYPE_CHECKING:
    from engine.input.handler import InputHandler
    from imgui_bundle import imgui
    import moderngl


@dataclass
class Dialog:
    """A complete dialog script."""
    id: str
    nodes: dict[str, DialogNode]
    start_node: str = "start"
    variables: dict[str, Any] = None

    def __post_init__(self):
        if self.variables is None:
            self.variables = {}

    def get_node(self, node_id: str) -> Optional[DialogNode]:
        """Get a dialog node by ID."""
        return self.nodes.get(node_id)


class DialogManager:
    """
    Manages dialog scripts and the dialog system.

    Handles:
    - Loading dialog scripts from JSON
    - Running dialogs
    - Processing typewriter effect
    - Handling choices
    """

    def __init__(
        self,
        events: EventBus,
        input_handler: InputHandler,
        dialogs_path: str = "game/data/dialog",
    ):
        self.events = events
        self.input = input_handler
        self.dialogs_path = Path(dialogs_path)

        # Dialog cache
        self._dialogs: dict[str, Dialog] = {}

        # Current state
        self._context: Optional[DialogContext] = None
        self._current_dialog: Optional[Dialog] = None

        # Callbacks
        self._on_dialog_end: Optional[callable] = None

        # Listen for dialog events
        events.subscribe(EngineEvent.SCENE_TRANSITION, self._on_scene_event)

    def _on_scene_event(self, data: dict) -> None:
        """Handle scene events that might trigger dialog."""
        if data.get('type') == 'dialog_start':
            dialog_id = data.get('dialog_id')
            if dialog_id:
                self.start_dialog(dialog_id)

    def load_dialog(self, dialog_id: str) -> Optional[Dialog]:
        """Load a dialog script from JSON."""
        if dialog_id in self._dialogs:
            return self._dialogs[dialog_id]

        path = self.dialogs_path / f"{dialog_id}.json"
        if not path.exists():
            print(f"Dialog not found: {path}")
            return None

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Parse nodes
        nodes = {}
        for node_data in data.get('nodes', []):
            node = DialogNode(
                id=node_data.get('id', ''),
                speaker=node_data.get('speaker', ''),
                text=node_data.get('text', ''),
                portrait=node_data.get('portrait'),
                next_node=node_data.get('next'),
                on_enter=node_data.get('on_enter'),
                on_exit=node_data.get('on_exit'),
            )

            # Parse choices
            for choice_data in node_data.get('choices', []):
                choice = DialogChoice(
                    text=choice_data.get('text', ''),
                    next_node=choice_data.get('next', ''),
                    condition=choice_data.get('condition'),
                    action=choice_data.get('action'),
                )
                node.choices.append(choice)

            nodes[node.id] = node

        dialog = Dialog(
            id=dialog_id,
            nodes=nodes,
            start_node=data.get('start', 'start'),
            variables=data.get('variables', {}),
        )

        self._dialogs[dialog_id] = dialog
        return dialog

    def start_dialog(
        self,
        dialog_id: str,
        context: Optional[DialogContext] = None,
    ) -> bool:
        """Start a dialog."""
        dialog = self.load_dialog(dialog_id)
        if not dialog:
            return False

        self._current_dialog = dialog

        # Use provided context or create temporary one
        if context:
            self._context = context
        else:
            self._context = DialogContext()

        # Initialize
        self._context.start_dialog(dialog_id, dialog.start_node)
        self._context.variables.update(dialog.variables)

        # Load first node
        first_node = dialog.get_node(dialog.start_node)
        if first_node:
            self._set_node(first_node)
            return True

        return False

    def _set_node(self, node: DialogNode) -> None:
        """Set the current dialog node."""
        if not self._context:
            return

        # Execute on_enter script
        if node.on_enter:
            self._execute_script(node.on_enter)

        # Filter choices by conditions
        valid_choices = []
        for choice in node.choices:
            if choice.condition:
                if self._evaluate_condition(choice.condition):
                    valid_choices.append(choice)
            else:
                valid_choices.append(choice)

        # Create node with filtered choices
        filtered_node = DialogNode(
            id=node.id,
            speaker=node.speaker,
            text=self._process_text(node.text),
            portrait=node.portrait,
            next_node=node.next_node,
            choices=valid_choices,
            on_exit=node.on_exit,
        )

        self._context.set_node(filtered_node)

    def _process_text(self, text: str) -> str:
        """Process text variables like {player_name}."""
        if not self._context:
            return text

        result = text
        for key, value in self._context.variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result

    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition expression."""
        if not self._context:
            return False

        try:
            # Create safe evaluation context
            context = {
                'vars': self._context.variables,
                **self._context.variables,
            }
            return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception as e:
            print(f"Dialog condition error: {e}")
            return False

    def _execute_script(self, script: str) -> None:
        """Execute a dialog script action."""
        if not self._context:
            return

        try:
            # Create safe execution context
            context = {
                'vars': self._context.variables,
                'set_var': lambda k, v: self._context.set_variable(k, v),
            }
            exec(script, {"__builtins__": {}}, context)
        except Exception as e:
            print(f"Dialog script error: {e}")

    def update(self, dt: float) -> None:
        """Update dialog system."""
        if not self._context or not self._context.is_active:
            return

        # Update typewriter
        self._context.update_typewriter(dt)

        # Handle input
        if self.input.is_action_pressed(Action.CONFIRM):
            self._on_confirm()
        elif self.input.is_action_pressed(Action.CANCEL):
            self._on_cancel()
        elif self.input.is_action_pressed(Action.MOVE_UP):
            self._context.select_prev_choice()
        elif self.input.is_action_pressed(Action.MOVE_DOWN):
            self._context.select_next_choice()

    def _on_confirm(self) -> None:
        """Handle confirm input."""
        if not self._context:
            return

        state = self._context.state

        if state == DialogState.DISPLAYING:
            # Skip typewriter
            self._context.skip_typewriter()

        elif state == DialogState.WAITING_INPUT:
            # Advance to next node
            self._advance()

        elif state == DialogState.CHOICE_OPEN:
            # Select choice
            choice = self._context.get_selected_choice()
            if choice:
                # Execute action
                if choice.action:
                    self._execute_script(choice.action)

                # Go to next node
                if choice.next_node:
                    self._go_to_node(choice.next_node)
                else:
                    self._end_dialog()

    def _on_cancel(self) -> None:
        """Handle cancel input."""
        if not self._context:
            return

        if self._context.state == DialogState.DISPLAYING:
            # Skip typewriter
            self._context.skip_typewriter()

    def _advance(self) -> None:
        """Advance to the next node."""
        if not self._context or not self._current_dialog:
            return

        current_node = self._current_dialog.get_node(self._context.current_node_id)
        if not current_node:
            self._end_dialog()
            return

        # Execute on_exit script
        if current_node.on_exit:
            self._execute_script(current_node.on_exit)

        # Go to next node
        if current_node.next_node:
            self._go_to_node(current_node.next_node)
        else:
            self._end_dialog()

    def _go_to_node(self, node_id: str) -> None:
        """Go to a specific node."""
        if not self._current_dialog:
            return

        if node_id == "end":
            self._end_dialog()
            return

        node = self._current_dialog.get_node(node_id)
        if node:
            self._set_node(node)
        else:
            print(f"Dialog node not found: {node_id}")
            self._end_dialog()

    def _end_dialog(self) -> None:
        """End the current dialog."""
        if self._context:
            self._context.end_dialog()
            self._context.state = DialogState.INACTIVE

        self._current_dialog = None

        # Emit event
        self.events.emit(EngineEvent.SCENE_TRANSITION, {
            'type': 'dialog_end',
        })

        # Call callback
        if self._on_dialog_end:
            self._on_dialog_end()

    def is_active(self) -> bool:
        """Check if dialog is currently active."""
        return self._context is not None and self._context.is_active

    def get_context(self) -> Optional[DialogContext]:
        """Get the current dialog context."""
        return self._context

    def set_variable(self, key: str, value: Any) -> None:
        """Set a dialog variable."""
        if self._context:
            self._context.set_variable(key, value)

    def on_dialog_end(self, callback: callable) -> None:
        """Set callback for when dialog ends."""
        self._on_dialog_end = callback


class DialogRenderer:
    """
    Renders dialog boxes using ImGui.

    Supports portrait texture rendering when a ModernGL context is provided.
    """

    def __init__(
        self,
        dialog_manager: DialogManager,
        ctx: Optional['moderngl.Context'] = None,
        portrait_base_path: str = "assets/portraits",
    ):
        self.manager = dialog_manager
        self._ctx = ctx
        self._portrait_base_path = portrait_base_path

        # Portrait texture cache
        self._portrait_textures: dict[str, 'moderngl.Texture'] = {}

        # Visual settings
        self.box_height = 150
        self.box_margin = 20
        self.portrait_size = 100
        self.text_padding = 15

        # Colors
        self.box_color = (0.1, 0.1, 0.15, 0.95)
        self.border_color = (0.4, 0.4, 0.5, 1.0)
        self.name_color = (0.9, 0.8, 0.5, 1.0)
        self.text_color = (1.0, 1.0, 1.0, 1.0)
        self.choice_color = (0.8, 0.8, 0.8, 1.0)
        self.choice_selected_color = (1.0, 0.9, 0.5, 1.0)

    def _load_portrait(self, portrait_id: str) -> Optional['moderngl.Texture']:
        """
        Load a portrait texture by ID.

        Args:
            portrait_id: Portrait identifier (filename or path)

        Returns:
            ModernGL texture or None if loading fails
        """
        if not self._ctx:
            return None

        # Check cache
        if portrait_id in self._portrait_textures:
            return self._portrait_textures[portrait_id]

        # Determine path
        import os
        if os.path.isabs(portrait_id):
            path = portrait_id
        elif os.path.exists(portrait_id):
            path = portrait_id
        else:
            # Try with base path
            path = os.path.join(self._portrait_base_path, portrait_id)
            if not os.path.exists(path):
                # Try adding .png extension
                path = os.path.join(self._portrait_base_path, f"{portrait_id}.png")

        if not os.path.exists(path):
            return None

        try:
            import pygame

            # Load with pygame
            surface = pygame.image.load(path)
            surface = surface.convert_alpha()

            # Flip vertically for OpenGL
            surface = pygame.transform.flip(surface, False, True)

            # Convert to texture
            width, height = surface.get_size()
            data = pygame.image.tostring(surface, 'RGBA', True)

            texture = self._ctx.texture((width, height), 4, data)
            texture.filter = (self._ctx.NEAREST, self._ctx.NEAREST)

            # Cache it
            self._portrait_textures[portrait_id] = texture
            return texture

        except Exception:
            return None

    def render(self, screen_width: int, screen_height: int) -> None:
        """Render the dialog box."""
        from imgui_bundle import imgui

        context = self.manager.get_context()
        if not context or not context.is_active:
            return

        # Calculate box position
        box_x = self.box_margin
        box_y = screen_height - self.box_height - self.box_margin
        box_width = screen_width - self.box_margin * 2

        # Set window position and size
        imgui.set_next_window_pos(imgui.ImVec2(box_x, box_y))
        imgui.set_next_window_size(imgui.ImVec2(box_width, self.box_height))

        flags = (
            imgui.WindowFlags_.no_title_bar |
            imgui.WindowFlags_.no_resize |
            imgui.WindowFlags_.no_move |
            imgui.WindowFlags_.no_scrollbar |
            imgui.WindowFlags_.no_collapse
        )

        # Apply styling
        imgui.push_style_color(imgui.Col_.window_bg, imgui.ImVec4(*self.box_color))
        imgui.push_style_color(imgui.Col_.border, imgui.ImVec4(*self.border_color))
        imgui.push_style_var(imgui.StyleVar_.window_border_size, 2.0)
        imgui.push_style_var(imgui.StyleVar_.window_rounding, 8.0)

        if imgui.begin("DialogBox", None, flags):
            # Portrait area (if any)
            text_start_x = self.text_padding

            if context.portrait:
                # Load portrait texture
                portrait_texture = self._load_portrait(context.portrait)

                imgui.begin_child(
                    "Portrait",
                    imgui.ImVec2(self.portrait_size, self.portrait_size),
                    imgui.ChildFlags_.borders,
                )

                if portrait_texture:
                    # Render the actual portrait texture
                    imgui.image(
                        portrait_texture.glo,
                        imgui.ImVec2(self.portrait_size - 8, self.portrait_size - 8),
                        imgui.ImVec2(0, 0),  # UV0
                        imgui.ImVec2(1, 1),  # UV1
                    )
                else:
                    # Fallback: show speaker name as placeholder
                    imgui.text(f"[{context.speaker}]")

                imgui.end_child()
                imgui.same_line()
                text_start_x = self.portrait_size + self.text_padding * 2

            # Text area
            imgui.begin_child(
                "DialogText",
                imgui.ImVec2(0, 0),
                imgui.ChildFlags_.none,
            )

            # Speaker name
            if context.speaker_name:
                imgui.push_style_color(
                    imgui.Col_.text,
                    imgui.ImVec4(*self.name_color)
                )
                imgui.text(context.speaker_name)
                imgui.pop_style_color()
                imgui.separator()

            # Dialog text
            imgui.push_style_color(
                imgui.Col_.text,
                imgui.ImVec4(*self.text_color)
            )
            imgui.text_wrapped(context.displayed_text)
            imgui.pop_style_color()

            # Choices
            if context.state == DialogState.CHOICE_OPEN:
                imgui.separator()
                for i, choice in enumerate(context.choices):
                    is_selected = (i == context.selected_choice)
                    color = (
                        self.choice_selected_color
                        if is_selected
                        else self.choice_color
                    )
                    imgui.push_style_color(
                        imgui.Col_.text,
                        imgui.ImVec4(*color)
                    )

                    prefix = "> " if is_selected else "  "
                    imgui.text(f"{prefix}{choice.text}")

                    imgui.pop_style_color()

            # Continue indicator
            if context.state == DialogState.WAITING_INPUT:
                imgui.same_line(imgui.get_window_width() - 30)
                imgui.text("...")

            imgui.end_child()

        imgui.end()

        imgui.pop_style_var(2)
        imgui.pop_style_color(2)
