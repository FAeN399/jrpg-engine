"""
Dialog module - conversation system for NPCs and events.

Provides:
- Dialog script loading and parsing
- Typewriter text effect
- Choice handling
- Variable substitution
- Conditional branching
"""

from framework.dialog.system import DialogManager, DialogRenderer, Dialog
from framework.dialog.parser import DialogParser, compile_dialog_file

__all__ = [
    "DialogManager",
    "DialogRenderer",
    "Dialog",
    "DialogParser",
    "compile_dialog_file",
]
