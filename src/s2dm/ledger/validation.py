"""Validate ledger annotations before they are applied to a schema."""

from pathlib import Path
from typing import NamedTuple

from modl.ledger import LedgerValidationError, validate_model_labels
from modl.models import ElementKind


class ModlElement(NamedTuple):
    """Identifies a type or member of a GraphQL schema to check against the concepts of a ledger.

    ``label`` is the type name, or ``Type.member`` for a field or an enum value. ``parent_label`` is
    ``None`` for a type, and the type name for a field or an enum value.
    """

    label: str
    kind: ElementKind
    parent_label: str | None


def validate_modl_annotation(elements: list[ModlElement], ledger_dir: Path) -> bool:
    """Return whether the model's ``(label, kind, parent_label)`` elements match the ledger at ``ledger_dir``."""
    try:
        validate_model_labels(elements, ledger_dir)
    except LedgerValidationError:
        return False
    return True
