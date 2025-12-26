"""
Dialog components - conversation state, speakers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Any

from engine.core.component import Component


class DialogState(Enum):
    """State of a dialog interaction."""
    INACTIVE = auto()
    STARTING = auto()
    DISPLAYING = auto()
    WAITING_INPUT = auto()
    CHOICE_OPEN = auto()
    ENDING = auto()


@dataclass
class DialogChoice:
    """A single dialog choice option."""
    text: str
    next_node: str = ""
    condition: Optional[str] = None  # Python expression to evaluate
    action: Optional[str] = None     # Python expression to execute
    disabled_text: Optional[str] = None  # Text when condition fails


@dataclass
class DialogNode:
    """A single dialog message/node."""
    id: str = ""
    speaker: str = ""
    text: str = ""
    portrait: Optional[str] = None
    next_node: Optional[str] = None
    choices: list[DialogChoice] = field(default_factory=list)
    on_enter: Optional[str] = None  # Script on entering node
    on_exit: Optional[str] = None   # Script on leaving node

    @property
    def has_choices(self) -> bool:
        return len(self.choices) > 0


@dataclass
class DialogSpeaker(Component):
    """
    Makes an entity able to speak in dialogs.

    Attributes:
        name: Display name in dialog box
        portrait_id: Default portrait asset ID
        dialog_id: ID of dialog script to run
        voice_pitch: For voice effects (optional)
        text_color: Custom text color (optional)
    """
    name: str = ""
    portrait_id: Optional[str] = None
    dialog_id: Optional[str] = None
    voice_pitch: float = 1.0
    text_color: Optional[tuple[int, int, int]] = None


@dataclass
class DialogContext(Component):
    """
    Runtime dialog state for the player/system.

    Attributes:
        state: Current dialog state
        current_dialog_id: ID of active dialog
        current_node_id: Current node in dialog
        displayed_text: Text shown so far (typewriter)
        full_text: Complete text of current node
        char_index: Character index for typewriter
        typewriter_speed: Characters per second
        speaker_name: Current speaker name
        portrait: Current portrait ID
        choices: Available choices
        selected_choice: Highlighted choice index
        variables: Dialog variables for conditions
    """
    state: DialogState = DialogState.INACTIVE
    current_dialog_id: Optional[str] = None
    current_node_id: Optional[str] = None
    displayed_text: str = ""
    full_text: str = ""
    char_index: float = 0.0
    typewriter_speed: float = 30.0
    speaker_name: str = ""
    portrait: Optional[str] = None
    choices: list[DialogChoice] = field(default_factory=list)
    selected_choice: int = 0
    variables: dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """Check if dialog is currently active."""
        return self.state not in (DialogState.INACTIVE, DialogState.ENDING)

    @property
    def is_text_complete(self) -> bool:
        """Check if typewriter effect is complete."""
        return self.displayed_text == self.full_text

    def start_dialog(self, dialog_id: str, start_node: str = "start") -> None:
        """Begin a new dialog."""
        self.state = DialogState.STARTING
        self.current_dialog_id = dialog_id
        self.current_node_id = start_node
        self.displayed_text = ""
        self.full_text = ""
        self.char_index = 0.0
        self.choices.clear()
        self.selected_choice = 0

    def set_node(self, node: DialogNode) -> None:
        """Set current dialog node."""
        self.current_node_id = node.id
        self.speaker_name = node.speaker
        self.portrait = node.portrait
        self.full_text = node.text
        self.displayed_text = ""
        self.char_index = 0.0
        self.choices = node.choices.copy()
        self.selected_choice = 0
        self.state = DialogState.DISPLAYING

    def update_typewriter(self, dt: float) -> None:
        """Update typewriter effect."""
        if self.state != DialogState.DISPLAYING:
            return

        if not self.is_text_complete:
            self.char_index += self.typewriter_speed * dt
            idx = int(self.char_index)
            self.displayed_text = self.full_text[:idx]

            if self.is_text_complete:
                if self.choices:
                    self.state = DialogState.CHOICE_OPEN
                else:
                    self.state = DialogState.WAITING_INPUT

    def skip_typewriter(self) -> None:
        """Skip to end of current text."""
        self.displayed_text = self.full_text
        self.char_index = float(len(self.full_text))
        if self.choices:
            self.state = DialogState.CHOICE_OPEN
        else:
            self.state = DialogState.WAITING_INPUT

    def select_next_choice(self) -> None:
        """Move to next choice option."""
        if self.choices:
            self.selected_choice = (self.selected_choice + 1) % len(self.choices)

    def select_prev_choice(self) -> None:
        """Move to previous choice option."""
        if self.choices:
            self.selected_choice = (self.selected_choice - 1) % len(self.choices)

    def get_selected_choice(self) -> Optional[DialogChoice]:
        """Get the currently selected choice."""
        if self.choices and 0 <= self.selected_choice < len(self.choices):
            return self.choices[self.selected_choice]
        return None

    def end_dialog(self) -> None:
        """End the current dialog."""
        self.state = DialogState.ENDING
        self.current_dialog_id = None
        self.current_node_id = None

    def set_variable(self, key: str, value: Any) -> None:
        """Set a dialog variable."""
        self.variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a dialog variable."""
        return self.variables.get(key, default)
