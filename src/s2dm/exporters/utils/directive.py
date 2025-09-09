from typing import Any

from graphql import FloatValueNode, GraphQLField, GraphQLObjectType, IntValueNode


def get_directive_arguments(element: GraphQLField | GraphQLObjectType, directive_name: str) -> dict[str, Any]:
    """
    Extracts the arguments of a specified directive from a GraphQL element.
    Args:
        element: The GraphQL element from which to extract the directive arguments.
        directive_name: The name of the directive whose arguments are to be extracted.
    Returns:
        dict[str, Any]: A dictionary containing the directive arguments with proper type conversion.
    """
    if not has_given_directive(element, directive_name) or not element.ast_node:
        return {}

    directive = next(d for d in element.ast_node.directives if d.name.value == directive_name)
    args: dict[str, Any] = {}

    for arg in directive.arguments:
        arg_name = arg.name.value
        if hasattr(arg.value, "value"):
            if isinstance(arg.value, IntValueNode):
                args[arg_name] = int(arg.value.value)
            elif isinstance(arg.value, FloatValueNode):
                args[arg_name] = float(arg.value.value)
            else:
                args[arg_name] = arg.value.value
        else:
            args[arg_name] = arg.value

    return args


def has_given_directive(element: GraphQLObjectType | GraphQLField, directive_name: str) -> bool:
    """Check whether a GraphQL element (field, object type) has a particular specified directive."""
    if element.ast_node and element.ast_node.directives:
        for directive in element.ast_node.directives:
            if directive.name.value == directive_name:
                return True
    return False


def get_argument_content(
    element: GraphQLObjectType | GraphQLField, directive_name: str, argument_name: str
) -> Any | None:
    """
    Extracts the comment from a GraphQL element (field or named type).

    Args:
        element (GraphQLNamedType | GraphQLField): The GraphQL element to extract the comment from.
        directive_name: The name of the directive whose arguments are to be extracted.
        argument_name: The name of the argument whose content is to be extracted.

    Returns:
        str | None: The comment if present, otherwise None.
    """
    args = get_directive_arguments(element, directive_name)
    return args.get(argument_name) if args and argument_name in args else None
