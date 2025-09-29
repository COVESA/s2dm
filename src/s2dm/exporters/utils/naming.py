from typing import Any

from caseconverter import camelcase, cobolcase, flatcase, kebabcase, macrocase, pascalcase, snakecase, titlecase
from graphql import (
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLUnionType,
    get_named_type,
)

from s2dm.exporters.utils.graphql_type import is_graphql_system_type

CASE_CONVERTERS = {
    "camelCase": camelcase,
    "PascalCase": pascalcase,
    "snake_case": snakecase,
    "kebab-case": kebabcase,
    "MACROCASE": macrocase,
    "COBOL-CASE": cobolcase,
    "flatcase": flatcase,
    "TitleCase": titlecase,
}

TYPE_CONTEXTS = {
    GraphQLObjectType: "object",
    GraphQLInterfaceType: "interface",
    GraphQLInputObjectType: "input",
    GraphQLEnumType: "enum",
    GraphQLUnionType: "union",
    GraphQLScalarType: "scalar",
}


def convert_name(name: str, target_case: str) -> str:
    """Convert a name to the specified case format.

    Args:
        name: The name to convert
        target_case: The target case format (e.g., "camelCase", "PascalCase", "snake_case")

    Returns:
        The converted name, or the original name if target_case is not supported
    """
    if target_case in CASE_CONVERTERS:
        return str(CASE_CONVERTERS[target_case](name))
    return name


def get_target_case_for_element(element_type: str, context: str, naming_config: dict[str, Any]) -> str | None:
    """Get the target case conversion for a specific element type and context.

    Args:
        element_type: The type of element (e.g., "type", "field", "enumValue", "argument")
        context: The context within the element type (e.g., "object", "interface", "input")
        naming_config: Configuration dictionary specifying case conversions

    Returns:
        The target case string (e.g., "camelCase", "PascalCase") or None if not configured
    """
    if element_type in naming_config:
        config_section = naming_config[element_type]
        if isinstance(config_section, dict) and context in config_section:
            return str(config_section[context])
        elif isinstance(config_section, str):
            return str(config_section)
    return None


def apply_naming_to_schema(schema: GraphQLSchema, naming_config: dict[str, Any]) -> None:
    """Apply naming conversion to a GraphQL schema by modifying it in place.

    Args:
        schema: The GraphQL schema to modify
        naming_config: Configuration dictionary specifying case conversions for different element types
    """

    types_to_rename = []
    for type_name, type_obj in schema.type_map.items():
        if is_graphql_system_type(type_name):
            continue

        context = TYPE_CONTEXTS.get(type(type_obj))
        if context:
            target_case = get_target_case_for_element("type", context, naming_config)
            if target_case:
                new_name = convert_name(type_name, target_case)
                if new_name != type_name:
                    types_to_rename.append((type_name, new_name, type_obj))

        if isinstance(type_obj, GraphQLObjectType | GraphQLInterfaceType | GraphQLInputObjectType):
            convert_field_names(type_obj, naming_config, schema)
        elif isinstance(type_obj, GraphQLEnumType):
            convert_enum_values(type_obj, naming_config)

    for old_name, new_name, type_obj in types_to_rename:
        del schema.type_map[old_name]
        type_obj.name = new_name
        schema.type_map[new_name] = type_obj


def is_instance_tag_field(field_name: str, field: Any, schema: GraphQLSchema) -> bool:
    """Check if a field is an instanceTag field that should not be renamed.

    Args:
        field_name: Name of the field to check
        field: The GraphQL field object
        schema: The GraphQL schema containing the field's type

    Returns:
        True if this is an instanceTag field that should preserve its name
    """
    if field_name != "instanceTag":
        return False

    field_type = get_named_type(field.type)
    target_type = schema.get_type(field_type.name)

    if not isinstance(target_type, GraphQLObjectType):
        return False

    if target_type.ast_node and target_type.ast_node.directives:
        for directive in target_type.ast_node.directives:
            if directive.name.value == "instanceTag":
                return True
    return False


def convert_field_names(
    type_obj: GraphQLObjectType | GraphQLInterfaceType | GraphQLInputObjectType,
    naming_config: dict[str, Any],
    schema: GraphQLSchema,
) -> None:
    """Convert field names and argument names for a GraphQL type object.

    Args:
        type_obj: The GraphQL type object to modify
        naming_config: Configuration dictionary specifying case conversions
        schema: The GraphQL schema (used for instanceTag field detection)
    """
    context = TYPE_CONTEXTS.get(type(type_obj))
    if not context:
        return

    target_case = get_target_case_for_element("field", context, naming_config)
    if target_case:
        new_fields = {}
        for old_name, field in type_obj.fields.items():
            if is_instance_tag_field(old_name, field, schema):
                new_fields[old_name] = field
            else:
                new_name = convert_name(old_name, target_case)
                new_fields[new_name] = field

        type_obj.fields.clear()
        type_obj.fields.update(new_fields)

    if context in ("object", "interface"):
        for field in type_obj.fields.values():
            if hasattr(field, "args") and field.args:
                # Convert argument names - need to update dictionary keys (args don't have .name attribute)
                arg_target_case = get_target_case_for_element("argument", "field", naming_config)
                if arg_target_case:
                    new_args = {}
                    for old_name, arg in field.args.items():
                        new_name = convert_name(old_name, arg_target_case)
                        new_args[new_name] = arg

                    # Replace the args dictionary
                    field.args.clear()
                    field.args.update(new_args)


def convert_enum_values(type_obj: GraphQLEnumType, naming_config: dict[str, Any]) -> None:
    """Convert enum value names for a GraphQL enum type.

    Args:
        type_obj: The GraphQL enum type to modify
        naming_config: Configuration dictionary specifying case conversions
    """
    target_case = get_target_case_for_element("enumValue", "", naming_config)
    if not target_case:
        return

    new_values = {}
    for old_name, enum_value in type_obj.values.items():
        new_name = convert_name(old_name, target_case)
        new_values[new_name] = enum_value

    type_obj.values.clear()
    type_obj.values.update(new_values)


def apply_naming_to_instance_values(instance_values: list[str], naming_config: dict[str, Any] | None) -> list[str]:
    """Apply naming conversion to instance tag values based on the naming configuration.

    Args:
        instance_values: List of enum values to convert
        naming_config: Naming configuration dictionary

    Returns:
        List of converted enum values
    """
    if not naming_config:
        return instance_values

    target_case = get_target_case_for_element("instanceTag", "", naming_config)
    if not target_case:
        return instance_values

    return [convert_name(value, target_case) for value in instance_values]
