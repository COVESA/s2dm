"""Parser for graphql-inspector diff JSON output.

This module parses the JSON output from graphql-inspector Node.js script
into a structured format that can be easily consumed by other parts of the system.
"""

import json
from typing import Any

from pydantic import BaseModel, Field

from s2dm import log


class DiffChange(BaseModel):
    """A single change detected in the schema diff.

    Attributes:
        type: Type of change (e.g., "FIELD_TYPE_CHANGED", "ENUM_VALUE_ADDED")
        action: Action type - "insert", "update", or "delete"
        criticality: Criticality level - "BREAKING", "DANGEROUS", or "NON_BREAKING"
        path: Full path to the changed concept (e.g., "Vehicle.averageSpeed")
        concept_name: Name of the concept that needs variant increment
        message: Human-readable message describing the change
        type_name: Name of the type containing the change (optional)
        field_name: Name of the field that changed (optional)
        field: Alternative field path (optional)
        meta: Additional metadata about the change (optional)
    """

    type: str = Field(..., description="Type of change")
    action: str = Field(..., description="Action type: insert, update, or delete")
    criticality: str = Field(..., description="Criticality level: BREAKING, DANGEROUS, or NON_BREAKING")
    path: str = Field("", description="Full path to the changed concept")
    concept_name: str = Field("", description="Name of the concept that needs variant increment")
    message: str = Field("", description="Human-readable message describing the change")
    type_name: str | None = Field(None, description="Name of the type containing the change")
    field_name: str | None = Field(None, description="Name of the field that changed")
    field: str | None = Field(None, description="Alternative field path")
    meta: dict[str, Any] | None = Field(None, description="Additional metadata about the change")


def parse_diff_output(raw_output: str) -> list[DiffChange]:
    """Parse graphql-inspector diff JSON output into structured format.

    Args:
        raw_output: JSON string output from graphql-inspector Node.js script

    Returns:
        List of DiffChange instances with validated diff information

    Raises:
        json.JSONDecodeError: If the output is not valid JSON
        ValueError: If the JSON structure is invalid
    """
    try:
        json_data = json.loads(raw_output)

        # Validate structure - expect a JSON array
        if not isinstance(json_data, list):
            raise ValueError("Invalid diff output: expected a JSON array")

        # Parse changes into Pydantic models
        return [DiffChange.model_validate(change) for change in json_data]
    except json.JSONDecodeError as e:
        log.error(f"Failed to parse JSON output from graphql-inspector: {e}")
        log.error(f"Output: {raw_output[:500]}")
        raise
