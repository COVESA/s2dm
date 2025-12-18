"""Variant ID models and helpers."""

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class VariantEntry(BaseModel):
    """Entry for a single concept in the variant ID file."""

    id: str = Field(..., description="Variant-based ID in format Concept/vM.m (semantic version)")
    variant_counter: int = Field(
        default=1,
        description="Counter that increments with each change to this specific concept",
    )
    removed_in_version: str | None = Field(
        None,
        description="Version/tag when the concept was removed from the schema",
    )

    @staticmethod
    def _parse_semantic_version_from_id(id_str: str) -> tuple[int, int]:
        """Parse semantic version (major, minor) from ID string.

        Args:
            id_str: ID string in format "Concept/vM.m" (e.g., "Vehicle.speed/v1.0")

        Returns:
            Tuple of (major, minor) version numbers

        Raises:
            ValueError: If ID format is invalid
        """
        if "/v" not in id_str:
            raise ValueError(f"Invalid ID format: {id_str}. Expected format: Concept/vM.m")
        try:
            variant_part = id_str.split("/v")[-1]
            # Match semantic version pattern (M.m where M and m are integers)
            match = re.match(r"^(\d+)\.(\d+)$", variant_part)
            if not match:
                raise ValueError(f"Invalid semantic version format: {variant_part}. Expected format: M.m")
            major = int(match.group(1))
            minor = int(match.group(2))
            return (major, minor)
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid ID format: {id_str}. Variant must be semantic version (M.m).") from e

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Validate that ID follows the format Concept/vM.m."""
        cls._parse_semantic_version_from_id(v)
        return v

    @property
    def variant(self) -> tuple[int, int]:
        """Extract semantic version (major, minor) from the ID string.

        Returns:
            Tuple of (major, minor) version numbers
        """
        return self._parse_semantic_version_from_id(self.id)


class VariantIDFile(BaseModel):
    """Complete variant ID file structure."""

    version_tag: str
    concepts: dict[str, VariantEntry] = Field(
        default_factory=dict,
        description="Dictionary mapping concept names to their variant ID entries",
    )

    @classmethod
    def load(cls, path: Path) -> "VariantIDFile":
        """Load a variant ID file from a JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)

    def save(self, path: Path) -> None:
        """Save the variant ID file to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(exclude_none=True), f, indent=2)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return self.model_dump(exclude_none=True)
