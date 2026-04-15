import click
import langcodes
from linkml_runtime.utils.metamodelcore import URI


def validate_language_tag(ctx: click.Context, param: click.Parameter, value: str) -> str:
    """Validate if a given string is compliant to BCP 47 language tag standard.

    Args:
        ctx: Click context
        param: Click parameter
        value: The language tag to validate

    Returns:
        The validated language tag string

    Raises:
        click.BadParameter: If the language tag is invalid
    """
    # Check for basic validity first
    if not value.strip():
        raise click.BadParameter("Language tag cannot be empty")

    # Check for valid BCP 47 format using langcodes
    try:
        if not langcodes.get(value).is_valid():
            raise click.BadParameter(f"'{value}' is not a valid BCP 47 language tag")
    except ValueError as e:
        # Handle langcodes.LanguageTagError (inherits from ValueError)
        raise click.BadParameter(f"'{value}' is not a valid BCP 47 language tag: {str(e)}") from None

    return value


def validate_linkml_uri_value(value: str) -> str:
    """Validate a value against LinkML URI semantics.

    Args:
        value: The URI value to validate

    Returns:
        The validated and trimmed URI string

    Raises:
        ValueError: If the URI is empty or invalid
    """
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError("Value cannot be empty")
    if not URI.is_valid(normalized_value):
        raise ValueError(f"'{value}' is not a valid LinkML URI value")
    return normalized_value


def validate_linkml_uri(ctx: click.Context, param: click.Parameter, value: str) -> str:
    """Validate a LinkML URI value for Click options.

    Args:
        ctx: Click context
        param: Click parameter
        value: The URI value to validate

    Returns:
        The validated and trimmed URI string

    Raises:
        click.BadParameter: If the URI is empty or invalid
    """
    try:
        return validate_linkml_uri_value(value)
    except ValueError as error:
        raise click.BadParameter(str(error)) from None
