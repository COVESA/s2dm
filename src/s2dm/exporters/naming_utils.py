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
)


def convert_name(name: str, target_case: str) -> str:
    case_converters = {
        "camelCase": camelcase,
        "PascalCase": pascalcase,
        "snake_case": snakecase,
        "kebab-case": kebabcase,
        "MACROCASE": macrocase,
        "COBOL-CASE": cobolcase,
        "flatcase": flatcase,
        "TitleCase": titlecase,
    }

    if target_case in case_converters:
        return str(case_converters[target_case](name))
    return name


def get_target_case_for_element(element_type: str, context: str, naming_config: dict[str, Any]) -> str | None:
    if element_type in naming_config:
        config_section = naming_config[element_type]
        if isinstance(config_section, dict) and context in config_section:
            return str(config_section[context])
        elif isinstance(config_section, str):
            return str(config_section)
    return None


def apply_naming_to_schema(schema: GraphQLSchema, naming_config: dict[str, Any]) -> GraphQLSchema:
    """Apply naming conversion to a GraphQL schema by modifying object names directly."""
    type_contexts = {
        GraphQLObjectType: "object",
        GraphQLInterfaceType: "interface",
        GraphQLInputObjectType: "input",
        GraphQLEnumType: "enum",
        GraphQLUnionType: "union",
        GraphQLScalarType: "scalar",
    }

    new_type_map = {}
    for type_name, type_obj in schema.type_map.items():
        if type_name.startswith("__") or type_name in {
            "String",
            "Int",
            "Float",
            "Boolean",
            "ID",
            "Query",
            "Mutation",
            "Subscription",
        }:
            new_type_map[type_name] = type_obj
            continue

        context = type_contexts.get(type(type_obj))
        if context:
            target_case = get_target_case_for_element("type", context, naming_config)
            if target_case:
                new_name = convert_name(type_name, target_case)
                if new_name != type_name:
                    type_obj.name = new_name
                    new_type_map[new_name] = type_obj
                    continue

        new_type_map[type_name] = type_obj

    for type_obj in new_type_map.values():
        if isinstance(type_obj, GraphQLObjectType | GraphQLInterfaceType | GraphQLInputObjectType):
            convert_field_names(type_obj, naming_config)
        elif isinstance(type_obj, GraphQLEnumType):
            convert_enum_values(type_obj, naming_config)

    return GraphQLSchema(
        query=schema.query_type,
        mutation=schema.mutation_type,
        subscription=schema.subscription_type,
        types=list(new_type_map.values()),
        directives=schema.directives,
        description=schema.description,
        extensions=schema.extensions,
    )


def convert_names_in_collection(
    collection: dict[str, Any], element_type: str, context: str, naming_config: dict[str, Any]
) -> None:
    target_case = get_target_case_for_element(element_type, context, naming_config)
    if not target_case:
        return

    for name, item in collection.items():
        new_name = convert_name(name, target_case)
        if new_name != name:
            item.name = new_name


def convert_field_names(
    type_obj: GraphQLObjectType | GraphQLInterfaceType | GraphQLInputObjectType, naming_config: dict[str, Any]
) -> None:
    type_contexts = {GraphQLObjectType: "object", GraphQLInterfaceType: "interface", GraphQLInputObjectType: "input"}

    context = type_contexts.get(type(type_obj))
    if not context:
        return

    target_case = get_target_case_for_element("field", context, naming_config)
    if target_case:
        new_fields = {}
        for old_name, field in type_obj.fields.items():
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
    target_case = get_target_case_for_element("enumValue", "", naming_config)
    if not target_case:
        return

    new_values = {}
    for old_name, enum_value in type_obj.values.items():
        new_name = convert_name(old_name, target_case)
        new_values[new_name] = enum_value

    type_obj.values.clear()
    type_obj.values.update(new_values)
