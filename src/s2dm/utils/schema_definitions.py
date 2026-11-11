"""Superset comparisons over GraphQL schema definitions.

These predicates decide whether one declaration of a directive, scalar, or enum can safely
replace another during schema composition. They compare definition AST nodes structurally, so
they are independent of any exporter and are shared by the dependency composition resolver.
"""

from graphql import (
    ArgumentNode,
    DirectiveDefinitionNode,
    DirectiveNode,
    EnumTypeDefinitionNode,
    FieldDefinitionNode,
    InputValueDefinitionNode,
    NonNullTypeNode,
    ScalarTypeDefinitionNode,
)

from s2dm.utils.sequence import get_sequence_or_empty


def is_required_input_value_definition(argument: InputValueDefinitionNode) -> bool:
    """Return whether an AST input value definition must be provided by callers."""
    is_non_null = isinstance(argument.type, NonNullTypeNode)
    has_default = argument.default_value is not None
    return is_non_null and not has_default


def is_directive_definition_superset(
    candidate: DirectiveDefinitionNode,
    definition: DirectiveDefinitionNode,
) -> bool:
    """Return whether a directive definition can safely replace another definition."""
    if candidate.name.value != definition.name.value:
        return False
    if definition.repeatable and not candidate.repeatable:
        return False

    candidate_locations = {location.value for location in candidate.locations}
    definition_locations = {location.value for location in definition.locations}
    if not definition_locations.issubset(candidate_locations):
        return False

    candidate_arguments = {argument.name.value: argument for argument in get_sequence_or_empty(candidate.arguments)}
    definition_arguments = {argument.name.value: argument for argument in get_sequence_or_empty(definition.arguments)}
    return _is_input_value_definitions_superset(candidate_arguments, definition_arguments)


def is_field_definition_superset(
    candidate: FieldDefinitionNode,
    definition: FieldDefinitionNode,
) -> bool:
    """Return whether a field definition can safely replace another field definition.

    The return type must be identical, every argument the definition declares must have an identical
    argument in the candidate (extra candidate arguments are allowed only when optional), and every
    directive applied to the field must be a superset of the definition's.
    """
    if candidate.name.value != definition.name.value or candidate.type.to_dict() != definition.type.to_dict():
        return False

    candidate_arguments = {argument.name.value: argument for argument in get_sequence_or_empty(candidate.arguments)}
    definition_arguments = {argument.name.value: argument for argument in get_sequence_or_empty(definition.arguments)}
    if not _is_input_value_definitions_superset(candidate_arguments, definition_arguments):
        return False

    return is_applied_directives_superset(candidate.directives, definition.directives)


def _is_input_value_definitions_superset(
    candidate_arguments: dict[str, InputValueDefinitionNode],
    definition_arguments: dict[str, InputValueDefinitionNode],
) -> bool:
    for definition_argument in definition_arguments.values():
        if not _has_matching_input_value_definition(candidate_arguments, definition_argument):
            return False

    for argument_name, candidate_argument in candidate_arguments.items():
        if argument_name in definition_arguments:
            continue
        if is_required_input_value_definition(candidate_argument):
            return False

    return True


def is_applied_directive_superset(candidate: DirectiveNode, definition: DirectiveNode) -> bool:
    """Return whether an applied directive can safely replace another applied directive."""
    if candidate.name.value != definition.name.value:
        return False

    candidate_arguments = {argument.name.value: argument for argument in get_sequence_or_empty(candidate.arguments)}
    definition_arguments = {argument.name.value: argument for argument in get_sequence_or_empty(definition.arguments)}
    for definition_argument in definition_arguments.values():
        if not _has_matching_applied_argument_value(candidate_arguments, definition_argument):
            return False

    return True


def _has_matching_input_value_definition(
    candidate_arguments: dict[str, InputValueDefinitionNode],
    definition_argument: InputValueDefinitionNode,
) -> bool:
    candidate_argument = candidate_arguments.get(definition_argument.name.value)
    return candidate_argument is not None and candidate_argument.to_dict() == definition_argument.to_dict()


def _has_matching_applied_argument_value(
    candidate_arguments: dict[str, ArgumentNode],
    definition_argument: ArgumentNode,
) -> bool:
    candidate_argument = candidate_arguments.get(definition_argument.name.value)
    return candidate_argument is not None and candidate_argument.value.to_dict() == definition_argument.value.to_dict()


def is_applied_directives_superset(
    candidate_directives: tuple[DirectiveNode, ...] | None,
    definition_directives: tuple[DirectiveNode, ...] | None,
) -> bool:
    """Return whether one set of applied directives is a superset of another."""
    if not definition_directives:
        return True

    candidate_directives_by_name = {
        directive.name.value: directive for directive in get_sequence_or_empty(candidate_directives)
    }
    for definition_directive in definition_directives:
        candidate_directive = candidate_directives_by_name.get(definition_directive.name.value)
        if candidate_directive is None or not is_applied_directive_superset(candidate_directive, definition_directive):
            return False

    return True


def is_scalar_definition_superset(
    candidate: ScalarTypeDefinitionNode,
    definition: ScalarTypeDefinitionNode,
) -> bool:
    """Return whether a scalar definition can safely replace another scalar definition."""
    if candidate.name.value != definition.name.value:
        return False
    return is_applied_directives_superset(candidate.directives, definition.directives)


def is_enum_definition_superset(
    candidate: EnumTypeDefinitionNode,
    definition: EnumTypeDefinitionNode,
) -> bool:
    """Return whether an enum definition can safely replace another enum definition.

    The candidate must declare every value the definition declares (it may add more), and every
    directive applied to the enum or to a shared value must be a superset of the definition's.
    """
    if candidate.name.value != definition.name.value or not is_applied_directives_superset(
        candidate.directives, definition.directives
    ):
        return False

    candidate_values = {value.name.value: value for value in get_sequence_or_empty(candidate.values)}
    for definition_value in get_sequence_or_empty(definition.values):
        candidate_value = candidate_values.get(definition_value.name.value)
        if candidate_value is None or not is_applied_directives_superset(
            candidate_value.directives, definition_value.directives
        ):
            return False

    return True
