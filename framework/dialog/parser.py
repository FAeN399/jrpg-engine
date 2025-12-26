"""
Dialog parser - converts dialog scripts to JSON.

Supports a simple text-based dialog format:

```
# dialog_id
@speaker_name [portrait_id]
Some dialog text that can span
multiple lines.

>> Choice 1 -> next_node_1
>> Choice 2 -> next_node_2

---

# another_node
@another_speaker
More dialog text.
-> next_node
```
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedChoice:
    """A parsed choice option."""
    text: str
    next_node: str
    condition: Optional[str] = None
    action: Optional[str] = None


@dataclass
class ParsedNode:
    """A parsed dialog node."""
    id: str
    speaker: str = ""
    portrait: Optional[str] = None
    text: str = ""
    next_node: Optional[str] = None
    choices: list[ParsedChoice] = field(default_factory=list)
    on_enter: Optional[str] = None
    on_exit: Optional[str] = None


@dataclass
class ParsedDialog:
    """A complete parsed dialog."""
    id: str
    nodes: list[ParsedNode] = field(default_factory=list)
    start_node: str = "start"
    variables: dict = field(default_factory=dict)


class DialogParser:
    """
    Parses dialog scripts from a simple text format.
    """

    # Regex patterns
    NODE_PATTERN = re.compile(r'^#\s*(\w+)\s*$')
    SPEAKER_PATTERN = re.compile(r'^@(\w+)(?:\s*\[(\w+)\])?\s*$')
    CHOICE_PATTERN = re.compile(r'^>>\s*(.+?)\s*->\s*(\w+)(?:\s*\[(.+?)\])?\s*$')
    NEXT_PATTERN = re.compile(r'^->\s*(\w+)\s*$')
    SCRIPT_PATTERN = re.compile(r'^!\s*(.+)$')
    VARIABLE_PATTERN = re.compile(r'^\$(\w+)\s*=\s*(.+)$')

    def parse_file(self, path: str | Path) -> ParsedDialog:
        """Parse a dialog script file."""
        path = Path(path)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        dialog = self.parse_string(content)
        dialog.id = path.stem
        return dialog

    def parse_string(self, content: str) -> ParsedDialog:
        """Parse a dialog script string."""
        dialog = ParsedDialog(id="parsed")
        current_node: Optional[ParsedNode] = None
        text_lines: list[str] = []

        lines = content.split('\n')

        for line in lines:
            line = line.rstrip()

            # Skip empty lines (but preserve in text)
            if not line.strip():
                if current_node and text_lines:
                    text_lines.append('')
                continue

            # Skip comments
            if line.strip().startswith('//'):
                continue

            # Node separator
            if line.strip() == '---':
                if current_node:
                    current_node.text = '\n'.join(text_lines).strip()
                    dialog.nodes.append(current_node)
                    current_node = None
                    text_lines = []
                continue

            # Node ID
            match = self.NODE_PATTERN.match(line)
            if match:
                if current_node:
                    current_node.text = '\n'.join(text_lines).strip()
                    dialog.nodes.append(current_node)

                current_node = ParsedNode(id=match.group(1))
                text_lines = []
                continue

            # Variable definition (at file start)
            match = self.VARIABLE_PATTERN.match(line)
            if match and not current_node:
                key = match.group(1)
                value = match.group(2).strip()
                # Try to parse as JSON value
                try:
                    dialog.variables[key] = json.loads(value)
                except json.JSONDecodeError:
                    dialog.variables[key] = value
                continue

            # Inside a node
            if current_node:
                # Speaker line
                match = self.SPEAKER_PATTERN.match(line)
                if match:
                    current_node.speaker = match.group(1)
                    current_node.portrait = match.group(2)
                    continue

                # Choice
                match = self.CHOICE_PATTERN.match(line)
                if match:
                    choice = ParsedChoice(
                        text=match.group(1),
                        next_node=match.group(2),
                        condition=match.group(3),
                    )
                    current_node.choices.append(choice)
                    continue

                # Next node reference
                match = self.NEXT_PATTERN.match(line)
                if match:
                    current_node.next_node = match.group(1)
                    continue

                # Script line
                match = self.SCRIPT_PATTERN.match(line)
                if match:
                    script = match.group(1)
                    if script.startswith('enter:'):
                        current_node.on_enter = script[6:].strip()
                    elif script.startswith('exit:'):
                        current_node.on_exit = script[5:].strip()
                    continue

                # Regular text line
                text_lines.append(line)

        # Don't forget the last node
        if current_node:
            current_node.text = '\n'.join(text_lines).strip()
            dialog.nodes.append(current_node)

        # Set start node
        if dialog.nodes:
            dialog.start_node = dialog.nodes[0].id

        return dialog

    def to_json(self, dialog: ParsedDialog) -> dict:
        """Convert parsed dialog to JSON format."""
        return {
            'id': dialog.id,
            'start': dialog.start_node,
            'variables': dialog.variables,
            'nodes': [
                {
                    'id': node.id,
                    'speaker': node.speaker,
                    'portrait': node.portrait,
                    'text': node.text,
                    'next': node.next_node,
                    'on_enter': node.on_enter,
                    'on_exit': node.on_exit,
                    'choices': [
                        {
                            'text': choice.text,
                            'next': choice.next_node,
                            'condition': choice.condition,
                            'action': choice.action,
                        }
                        for choice in node.choices
                    ] if node.choices else None,
                }
                for node in dialog.nodes
            ],
        }

    def save_json(self, dialog: ParsedDialog, path: str | Path) -> None:
        """Save parsed dialog as JSON."""
        path = Path(path)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_json(dialog), f, indent=2)


def compile_dialog_file(input_path: str | Path, output_path: Optional[str | Path] = None) -> None:
    """
    Compile a dialog script to JSON.

    Args:
        input_path: Path to .dialog file
        output_path: Path to output .json file (default: same name with .json)
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.with_suffix('.json')
    else:
        output_path = Path(output_path)

    parser = DialogParser()
    dialog = parser.parse_file(input_path)
    parser.save_json(dialog, output_path)
    print(f"Compiled {input_path} -> {output_path}")
