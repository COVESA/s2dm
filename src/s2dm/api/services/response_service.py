"""Response construction service for API endpoints."""

import time
from collections.abc import Callable

from s2dm.api.models.base import ApiResponse, ResponseMetadata


def execute_and_respond(
    executor: Callable[[], list[str]],
    result_format: str,
) -> ApiResponse:
    """Execute a callable and construct an ApiResponse with timing metadata.

    Args:
        executor: Callable that performs the work and returns list of result strings
        result_format: Format identifier for the result (e.g., "avsc", "proto", "graphql")

    Returns:
        ApiResponse with result and timing metadata
    """
    start_time = time.perf_counter()

    result = executor()

    processing_time_ms = int((time.perf_counter() - start_time) * 1000)

    return ApiResponse(
        result=result,
        metadata=ResponseMetadata(result_format=result_format, processing_time_ms=processing_time_ms),
    )
