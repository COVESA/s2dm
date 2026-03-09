"""API configuration constants."""

from typing import Any

from s2dm.api.models.base import ErrorResponse

COMMON_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Bad request - invalid or missing fields"},
    500: {"model": ErrorResponse, "description": "Internal server error"},
}
