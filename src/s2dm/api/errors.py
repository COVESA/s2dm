"""API-specific error types and translation helpers."""

import yaml
from ariadne.exceptions import GraphQLFileSyntaxError
from graphql import GraphQLError, GraphQLSyntaxError
from pydantic import ValidationError
from rdflib.plugin import PluginException


class ResponseError(ValueError):
    """Validation-like error that is safe to expose to API clients."""


def to_response_error(exc: Exception) -> ResponseError | None:
    """Translate safe domain/library exceptions into API response errors."""
    if isinstance(exc, ResponseError):
        return exc

    if isinstance(exc, GraphQLSyntaxError | GraphQLError):
        return ResponseError(exc.message)

    if isinstance(exc, GraphQLFileSyntaxError):
        message = str(exc)
        _, separator, remainder = message.partition(":\n")
        return ResponseError(remainder if separator else message)

    if isinstance(exc, yaml.YAMLError):
        return ResponseError(f"Invalid naming config YAML: {exc}")

    if isinstance(exc, ValidationError):
        return ResponseError(str(exc))

    if isinstance(exc, PluginException):
        return ResponseError(str(exc))

    if isinstance(exc, ValueError | TypeError):
        return ResponseError(str(exc))

    return None
