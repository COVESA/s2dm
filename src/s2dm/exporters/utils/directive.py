import re
from typing import Any

from graphql import (
    FloatValueNode,
    GraphQLEnumType,
    GraphQLField,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLUnionType,
    IntValueNode,
)
from graphql.language.ast import StringValueNode


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


def format_directive_from_ast(directive_node: Any) -> str:
    directive_name = directive_node.name.value
    if directive_name in {"deprecated", "specifiedBy"}:
        return ""

    args_str = ""
    if directive_node.arguments:
        args_list = []
        for arg_node in directive_node.arguments:
            arg_name = arg_node.name.value
            if hasattr(arg_node.value, "value"):
                if isinstance(arg_node.value, StringValueNode):
                    arg_value = f'"{arg_node.value.value}"'
                else:
                    arg_value = str(arg_node.value.value)
            else:
                arg_value = str(arg_node.value)
            args_list.append(f"{arg_name}: {arg_value}")
        args_str = f"({', '.join(args_list)})"

    return f"@{directive_name}{args_str}"


def build_directive_map(schema: GraphQLSchema) -> dict[str | tuple[str, str], list[str]]:
    directive_map: dict[str | tuple[str, str], list[str]] = {}

    # Helper functions to avoid code duplication
    def has_directives(value: Any) -> bool:
        return bool(
            hasattr(value, "ast_node")
            and value.ast_node
            and hasattr(value.ast_node, "directives")
            and value.ast_node.directives
        )

    def get_directive_strings(value: Any) -> list[str]:
        directive_strings = []
        for directive_node in value.ast_node.directives:
            directive_str = format_directive_from_ast(directive_node)
            if directive_str:
                directive_strings.append(directive_str)
        return directive_strings

    DIRECTIVE_RELATED_TYPES = (
        GraphQLObjectType,
        GraphQLInterfaceType,
        GraphQLInputObjectType,
        GraphQLEnumType,
        GraphQLUnionType,
        GraphQLScalarType,
    )

    for type_name, type_obj in schema.type_map.items():
        if type_name.startswith("__") or not isinstance(
            type_obj,
            DIRECTIVE_RELATED_TYPES,
        ):
            continue

        # Directives on types
        if has_directives(type_obj):
            directive_strings = get_directive_strings(type_obj)
            if directive_strings:
                directive_map[type_name] = directive_strings

        # Directives on fields
        if hasattr(type_obj, "fields"):
            for field_name, field in type_obj.fields.items():
                if has_directives(field):
                    directive_strings = get_directive_strings(field)
                    if directive_strings:
                        directive_map[(type_name, field_name)] = directive_strings

        # Directives on enums
        if isinstance(type_obj, GraphQLEnumType) and hasattr(type_obj, "values"):
            for enum_value_name, enum_value in type_obj.values.items():
                if has_directives(enum_value):
                    directive_strings = get_directive_strings(enum_value)
                    if directive_strings:
                        directive_map[(type_name, enum_value_name)] = directive_strings

    return directive_map


def add_directives_to_schema(schema_str: str, directive_map: dict[str | tuple[str, str], list[str]]) -> str:
    lines = schema_str.split("\n")
    result_lines = []
    current_type = None

    for line in lines:
        type_match = re.match(r"^(type|interface|input|enum|union|scalar)\s+(\w+)", line)
        if type_match:
            type_kind = type_match.group(1)
            type_name = type_match.group(2)
            current_type = type_name

            if type_name in directive_map:
                directives_str = " " + " ".join(directive_map[type_name])
                line = line.replace(f"{type_kind} {type_name}", f"{type_kind} {type_name}{directives_str}")

        elif current_type:
            field_match = re.match(r"^\s+(\w+)(?:\([^)]*\))?\s*:\s*", line)
            if field_match:
                field_name = field_match.group(1)
                if current_type and (current_type, field_name) in directive_map:
                    directives_str = " " + " ".join(directive_map[(current_type, field_name)])
                    line = line.rstrip() + directives_str

            enum_match = re.match(r"^\s+(\w+)\s*$", line)
            if enum_match:
                enum_value_name = enum_match.group(1)
                if current_type and (current_type, enum_value_name) in directive_map:
                    directives_str = " " + " ".join(directive_map[(current_type, enum_value_name)])
                    line = line.rstrip() + directives_str

        if line.strip() == "}":
            current_type = None

        result_lines.append(line)

    return "\n".join(result_lines)
