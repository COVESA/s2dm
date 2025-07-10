import click
import langcodes


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
