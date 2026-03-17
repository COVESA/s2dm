from pathlib import Path
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

from s2dm.exporters.utils.directive import has_given_directive
from s2dm.exporters.utils.graphql_type import is_graphql_system_type
from s2dm.exporters.utils.naming_config import (
    CaseFormat,
    ContextType,
    ElementType,
    NamingConventionConfig,
    get_case_for_element,
    load_naming_convention_config,
)

CASE_CONVERTERS = {
    CaseFormat.CAMEL_CASE: camelcase,
    CaseFormat.PASCAL_CASE: pascalcase,
    CaseFormat.SNAKE_CASE: snakecase,
    CaseFormat.KEBAB_CASE: kebabcase,
    CaseFormat.MACRO_CASE: macrocase,
    CaseFormat.COBOL_CASE: cobolcase,
    CaseFormat.FLAT_CASE: flatcase,
    CaseFormat.TITLE_CASE: titlecase,
}

TYPE_CONTEXTS = {
    GraphQLObjectType: ContextType.OBJECT,
    GraphQLInterfaceType: ContextType.INTERFACE,
    GraphQLInputObjectType: ContextType.INPUT,
    GraphQLEnumType: ContextType.ENUM,
    GraphQLUnionType: ContextType.UNION,
    GraphQLScalarType: ContextType.SCALAR,
}


def convert_name(name: str, target_case: CaseFormat) -> str:
    """Convert a name to the specified case format.

    Args:
        name: The name to convert
        target_case: The target case format

    Returns:
        The converted name
    """
    return str(CASE_CONVERTERS[target_case](name))


def _collect_instance_tag_enum_names(schema: GraphQLSchema) -> set[str]:
    """Collect names of enum types used as fields of @instanceTag object types."""
    instance_tag_enum_names: set[str] = set()
    for type_obj in schema.type_map.values():
        if not isinstance(type_obj, GraphQLObjectType) or not has_given_directive(type_obj, "instanceTag"):
            continue
        for field in type_obj.fields.values():
            field_base_type = get_named_type(field.type)
            field_type_obj = schema.get_type(field_base_type.name)
            if isinstance(field_type_obj, GraphQLEnumType):
                instance_tag_enum_names.add(field_base_type.name)
    return instance_tag_enum_names


def apply_naming_to_schema(schema: GraphQLSchema, naming_config: NamingConventionConfig) -> None:
    """Apply naming conversion to a GraphQL schema by modifying it in place.

    Args:
        schema: The GraphQL schema to modify
        naming_config: Naming convention configuration
    """
    instance_tag_enum_names = _collect_instance_tag_enum_names(schema)

    types_to_rename = []
    for type_name, type_obj in schema.type_map.items():
        if is_graphql_system_type(type_name):
            continue

        context = TYPE_CONTEXTS.get(type(type_obj))
        if context:
            target_case = get_case_for_element(ElementType.TYPE, context, naming_config)
            if target_case:
                new_name = convert_name(type_name, target_case)
                if new_name != type_name:
                    types_to_rename.append((type_name, new_name, type_obj))

        if isinstance(type_obj, GraphQLObjectType | GraphQLInterfaceType | GraphQLInputObjectType):
            convert_field_names(type_obj, naming_config, schema)
        elif isinstance(type_obj, GraphQLEnumType):
            if type_name in instance_tag_enum_names:
                convert_enum_values(type_obj, naming_config, element_type=ElementType.INSTANCE_TAG)
            else:
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
    naming_config: NamingConventionConfig,
    schema: GraphQLSchema,
) -> None:
    """Convert field names and argument names for a GraphQL type object.

    Args:
        type_obj: The GraphQL type object to modify
        naming_config: Naming convention configuration
        schema: The GraphQL schema (used for instanceTag field detection)
    """
    context = TYPE_CONTEXTS.get(type(type_obj))
    if not context:
        return

    target_case = get_case_for_element(ElementType.FIELD, context, naming_config)
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

    if context in (ContextType.OBJECT, ContextType.INTERFACE):
        for field in type_obj.fields.values():
            if field.args:
                arg_target_case = get_case_for_element(ElementType.ARGUMENT, ContextType.FIELD, naming_config)
                if arg_target_case:
                    new_args = {}
                    for old_name, arg in field.args.items():
                        new_name = convert_name(old_name, arg_target_case)
                        new_args[new_name] = arg

                    field.args.clear()
                    field.args.update(new_args)


def convert_enum_values(
    type_obj: GraphQLEnumType,
    naming_config: NamingConventionConfig,
    element_type: ElementType = ElementType.ENUM_VALUE,
) -> None:
    """Convert enum value names for a GraphQL enum type.

    Args:
        type_obj: The GraphQL enum type to modify
        naming_config: Naming convention configuration
        element_type: Which naming rule to apply (ENUM_VALUE for regular enums,
            INSTANCE_TAG for enums used inside @instanceTag types)
    """
    target_case = get_case_for_element(element_type, None, naming_config)
    if not target_case:
        return

    new_values = {}
    for old_name, enum_value in type_obj.values.items():
        new_name = convert_name(old_name, target_case)
        new_values[new_name] = enum_value

    type_obj.values.clear()
    type_obj.values.update(new_values)


def apply_naming_to_instance_values(
    instance_values: list[str], naming_config: NamingConventionConfig | None
) -> list[str]:
    """Apply naming conversion to instance tag values based on the naming configuration.

    Args:
        instance_values: List of enum values to convert
        naming_config: Naming convention configuration

    Returns:
        List of converted enum values
    """
    if not naming_config:
        return instance_values

    target_case = get_case_for_element(ElementType.INSTANCE_TAG, None, naming_config)
    if not target_case:
        return instance_values

    return [convert_name(value, target_case) for value in instance_values]


def load_naming_config(config_path: Path | None) -> NamingConventionConfig | None:
    """Load naming configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Naming convention configuration or None if no path provided
    """
    return load_naming_convention_config(config_path)
