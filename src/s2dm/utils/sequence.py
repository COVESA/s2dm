"""Sequence utility functions."""

from collections.abc import Sequence
from typing import TypeVar

_Item = TypeVar("_Item")


def get_sequence_or_empty(items: Sequence[_Item] | None) -> Sequence[_Item]:
    """Return the items, or an empty tuple when they are missing.

    Args:
        items: The items, or ``None`` when they are missing.

    Returns:
        Sequence[_Item]: The given items, or an empty tuple.
    """
    if items is None:
        return ()
    return items
