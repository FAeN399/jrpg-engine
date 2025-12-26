"""
Field editors for Pydantic model fields.

Provides ImGui widgets for editing Pydantic BaseModel fields
with support for various types including primitives, enums,
lists, dicts, and nested models.
"""

from __future__ import annotations

from dataclasses import fields as dataclass_fields, is_dataclass
from enum import Enum
from typing import Any, get_origin, get_args, Union
from types import UnionType, NoneType

from imgui_bundle import imgui
from pydantic import BaseModel
from pydantic.fields import FieldInfo


def render_field(
    label: str,
    value: Any,
    field_type: type,
    field_info: FieldInfo | None = None,
    indent: bool = False
) -> tuple[bool, Any]:
    """
    Render an appropriate editor for a field based on its type.

    Args:
        label: Display label
        value: Current value
        field_type: The field's type annotation
        field_info: Optional Pydantic FieldInfo for constraints
        indent: Whether to indent nested content

    Returns:
        Tuple of (changed: bool, new_value)
    """
    origin = get_origin(field_type)
    args = get_args(field_type)

    # Handle Optional[T] (Union[T, None] or T | None)
    if origin is Union or origin is UnionType:
        non_none_args = [a for a in args if a is not NoneType]
        if len(non_none_args) == 1:
            return render_optional_field(label, value, non_none_args[0], field_info)

    # Handle list[T]
    if origin is list:
        item_type = args[0] if args else Any
        return render_list_field(label, value, item_type)

    # Handle dict[K, V]
    if origin is dict:
        key_type = args[0] if args else str
        value_type = args[1] if len(args) > 1 else Any
        return render_dict_field(label, value, key_type, value_type)

    # Handle set[T]
    if origin is set:
        item_type = args[0] if args else Any
        return render_set_field(label, value, item_type)

    # Handle frozenset[T]
    if origin is frozenset:
        item_type = args[0] if args else Any
        return render_frozenset_field(label, value, item_type)

    # Handle tuple
    if origin is tuple:
        return render_tuple_field(label, value, args)

    # Handle Enum subclasses
    if isinstance(field_type, type) and issubclass(field_type, Enum):
        return render_enum_field(label, value, field_type)

    # Handle nested Pydantic models
    if isinstance(field_type, type) and issubclass(field_type, BaseModel):
        return render_nested_model(label, value, field_type)

    # Handle dataclasses
    if is_dataclass(field_type):
        return render_dataclass(label, value, field_type)

    # Primitive types
    if field_type is int:
        return render_int_field(label, value, field_info)
    if field_type is float:
        return render_float_field(label, value, field_info)
    if field_type is str:
        return render_str_field(label, value, field_info)
    if field_type is bool:
        return render_bool_field(label, value)

    # Fallback: read-only display
    return render_readonly_field(label, value)


def render_int_field(
    label: str,
    value: int,
    field_info: FieldInfo | None = None
) -> tuple[bool, int]:
    """Render an integer field with optional constraints."""
    min_val = None
    max_val = None

    # Extract constraints from field_info
    if field_info and field_info.metadata:
        for constraint in field_info.metadata:
            if hasattr(constraint, 'ge'):
                min_val = constraint.ge
            if hasattr(constraint, 'gt'):
                min_val = constraint.gt + 1
            if hasattr(constraint, 'le'):
                max_val = constraint.le
            if hasattr(constraint, 'lt'):
                max_val = constraint.lt - 1

    if min_val is not None and max_val is not None:
        # Use slider for bounded values
        changed, new_value = imgui.slider_int(label, value, int(min_val), int(max_val))
    else:
        # Use drag_int for unbounded
        changed, new_value = imgui.drag_int(label, value, 1.0)

    return changed, new_value


def render_float_field(
    label: str,
    value: float,
    field_info: FieldInfo | None = None
) -> tuple[bool, float]:
    """Render a float field."""
    min_val = None
    max_val = None

    if field_info and field_info.metadata:
        for constraint in field_info.metadata:
            if hasattr(constraint, 'ge'):
                min_val = constraint.ge
            if hasattr(constraint, 'le'):
                max_val = constraint.le

    if min_val is not None and max_val is not None:
        changed, new_value = imgui.slider_float(label, value, min_val, max_val)
    else:
        speed = 0.1
        changed, new_value = imgui.drag_float(label, value, speed)

    return changed, new_value


def render_str_field(
    label: str,
    value: str,
    field_info: FieldInfo | None = None
) -> tuple[bool, str]:
    """Render a string field."""
    # Determine if multiline
    max_length = 256

    if field_info and field_info.metadata:
        for constraint in field_info.metadata:
            if hasattr(constraint, 'max_length'):
                max_length = constraint.max_length

    # Use input_text for single line
    imgui.set_next_item_width(-1)
    changed, new_value = imgui.input_text(label, value)

    return changed, new_value


def render_bool_field(label: str, value: bool) -> tuple[bool, bool]:
    """Render a boolean checkbox."""
    changed, new_value = imgui.checkbox(label, value)
    return changed, new_value


def render_enum_field(
    label: str,
    value: Enum | None,
    enum_class: type[Enum]
) -> tuple[bool, Enum]:
    """Render an enum dropdown."""
    members = list(enum_class)
    current_idx = 0

    if value is not None:
        try:
            current_idx = members.index(value)
        except ValueError:
            current_idx = 0

    changed = False
    new_value = value if value is not None else members[0]

    # Create preview string
    preview = value.name if value is not None else members[0].name

    if imgui.begin_combo(label, preview):
        for i, member in enumerate(members):
            is_selected = member == value
            if imgui.selectable(member.name, is_selected)[0]:
                new_value = member
                changed = True
            if is_selected:
                imgui.set_item_default_focus()
        imgui.end_combo()

    return changed, new_value


def render_optional_field(
    label: str,
    value: Any,
    inner_type: type,
    field_info: FieldInfo | None = None
) -> tuple[bool, Any]:
    """Render an optional field with None toggle."""
    changed = False
    new_value = value

    is_set = value is not None

    # Checkbox to toggle None
    checkbox_changed, is_set_new = imgui.checkbox(f"##{label}_set", is_set)
    imgui.same_line()

    if checkbox_changed:
        changed = True
        if is_set_new:
            # Create default value
            new_value = _create_default_value(inner_type)
        else:
            new_value = None

    # Render the inner field if set
    if is_set_new and new_value is not None:
        inner_changed, inner_value = render_field(label, new_value, inner_type, field_info)
        if inner_changed:
            changed = True
            new_value = inner_value
    else:
        imgui.text_disabled(f"{label}: None")

    return changed, new_value


def render_list_field(
    label: str,
    value: list,
    item_type: type
) -> tuple[bool, list]:
    """Render a list with add/remove buttons."""
    changed = False
    new_value = list(value) if value else []

    header_label = f"{label} ({len(new_value)} items)"
    if imgui.collapsing_header(header_label)[0]:
        imgui.indent()

        items_to_remove = []
        for i, item in enumerate(new_value):
            imgui.push_id(i)

            # Remove button
            if imgui.button("X"):
                items_to_remove.append(i)
                changed = True

            imgui.same_line()

            # Render item
            item_changed, new_item = render_field(f"[{i}]", item, item_type)
            if item_changed:
                new_value[i] = new_item
                changed = True

            imgui.pop_id()

        # Remove items in reverse order
        for i in reversed(items_to_remove):
            new_value.pop(i)

        # Add button
        if imgui.button(f"+ Add###{label}"):
            new_value.append(_create_default_value(item_type))
            changed = True

        imgui.unindent()

    return changed, new_value


def render_dict_field(
    label: str,
    value: dict,
    key_type: type,
    value_type: type
) -> tuple[bool, dict]:
    """Render a dictionary with key-value pairs."""
    changed = False
    new_value = dict(value) if value else {}

    header_label = f"{label} ({len(new_value)} entries)"
    if imgui.collapsing_header(header_label)[0]:
        imgui.indent()

        keys_to_remove = []
        for key in list(new_value.keys()):
            imgui.push_id(str(key))

            # Remove button
            if imgui.button("X"):
                keys_to_remove.append(key)
                changed = True

            imgui.same_line()

            # Key display (read-only for now)
            if isinstance(key, Enum):
                imgui.text(f"{key.name}:")
            else:
                imgui.text(f"{key}:")

            imgui.same_line()

            # Value editor
            val_changed, new_val = render_field(f"##{key}", new_value[key], value_type)
            if val_changed:
                new_value[key] = new_val
                changed = True

            imgui.pop_id()

        for key in keys_to_remove:
            del new_value[key]

        imgui.unindent()

    return changed, new_value


def render_set_field(
    label: str,
    value: set,
    item_type: type
) -> tuple[bool, set]:
    """Render a set as a list-like editor."""
    # Convert to list for editing
    as_list = list(value) if value else []
    changed, new_list = render_list_field(label, as_list, item_type)

    if changed:
        return True, set(new_list)
    return False, value


def render_frozenset_field(
    label: str,
    value: frozenset,
    item_type: type
) -> tuple[bool, frozenset]:
    """Render a frozenset (read-only display)."""
    items = list(value) if value else []
    header_label = f"{label} ({len(items)} items) [frozen]"

    if imgui.collapsing_header(header_label)[0]:
        imgui.indent()
        for i, item in enumerate(items):
            if isinstance(item, Enum):
                imgui.text(f"[{i}]: {item.name}")
            else:
                imgui.text(f"[{i}]: {item}")
        imgui.unindent()

    return False, value


def render_tuple_field(
    label: str,
    value: tuple,
    item_types: tuple
) -> tuple[bool, tuple]:
    """Render a tuple with fixed element types."""
    changed = False
    new_values = list(value) if value else []

    header_label = f"{label} ({len(new_values)} elements)"
    if imgui.collapsing_header(header_label)[0]:
        imgui.indent()

        for i, (item, item_type) in enumerate(zip(new_values, item_types)):
            imgui.push_id(i)
            item_changed, new_item = render_field(f"[{i}]", item, item_type)
            if item_changed:
                new_values[i] = new_item
                changed = True
            imgui.pop_id()

        imgui.unindent()

    if changed:
        return True, tuple(new_values)
    return False, value


def render_nested_model(
    label: str,
    value: BaseModel | None,
    model_class: type[BaseModel]
) -> tuple[bool, BaseModel]:
    """Render a nested Pydantic model."""
    changed = False

    if value is None:
        value = model_class()
        changed = True

    if imgui.collapsing_header(label)[0]:
        imgui.indent()

        for field_name, field_info in value.model_fields.items():
            # Skip private fields
            if field_name.startswith('_'):
                continue

            field_value = getattr(value, field_name)
            field_type = field_info.annotation

            imgui.push_id(field_name)
            field_changed, new_field_value = render_field(
                field_name,
                field_value,
                field_type,
                field_info
            )
            imgui.pop_id()

            if field_changed:
                setattr(value, field_name, new_field_value)
                changed = True

        imgui.unindent()

    return changed, value


def render_dataclass(
    label: str,
    value: Any,
    dataclass_type: type
) -> tuple[bool, Any]:
    """Render a dataclass instance."""
    changed = False

    if value is None:
        value = dataclass_type()
        changed = True

    if imgui.collapsing_header(label)[0]:
        imgui.indent()

        for field in dataclass_fields(dataclass_type):
            field_name = field.name
            field_type = field.type
            field_value = getattr(value, field_name)

            imgui.push_id(field_name)
            field_changed, new_field_value = render_field(
                field_name,
                field_value,
                field_type
            )
            imgui.pop_id()

            if field_changed:
                setattr(value, field_name, new_field_value)
                changed = True

        imgui.unindent()

    return changed, value


def render_readonly_field(label: str, value: Any) -> tuple[bool, Any]:
    """Render a read-only field display."""
    imgui.text_disabled(f"{label}: {value}")
    return False, value


def _create_default_value(field_type: type) -> Any:
    """Create a default value for a given type."""
    origin = get_origin(field_type)

    if origin is list:
        return []
    if origin is dict:
        return {}
    if origin is set:
        return set()
    if origin is tuple:
        return ()

    if field_type is int:
        return 0
    if field_type is float:
        return 0.0
    if field_type is str:
        return ""
    if field_type is bool:
        return False

    if isinstance(field_type, type):
        if issubclass(field_type, Enum):
            members = list(field_type)
            return members[0] if members else None

        if issubclass(field_type, BaseModel):
            return field_type()

        if is_dataclass(field_type):
            return field_type()

    return None
