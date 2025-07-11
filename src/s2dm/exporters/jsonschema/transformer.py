from typing import Any, cast

from graphql import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLType,
    GraphQLUnionType,
    is_enum_type,
    is_interface_type,
    is_list_type,
    is_non_null_type,
    is_object_type,
    is_scalar_type,
    is_union_type,
)
from graphql.language.ast import FloatValueNode, IntValueNode

from s2dm import log

from .traverser import get_referenced_types

GRAPHQL_SCALAR_TO_JSON_SCHEMA = {
    "String": "string",
    "Int": "integer",
    "Float": "number",
    "Boolean": "boolean",
    "ID": "string",
    "Int8": "integer",
    "UInt8": "integer",
    "Int16": "integer",
    "UInt16": "integer",
    "UInt32": "integer",
    "Int64": "integer",
    "UInt64": "integer",
}


def transform_to_json_schema(graphql_schema: GraphQLSchema, root_type: str | None = None) -> dict[str, Any]:
    """
    Transform a GraphQL schema to JSON Schema format.

    Converts all GraphQL types (except Query/Mutation/Subscription) into JSON Schema
    definitions in the $defs section. Handles directives as well.

    Args:
        graphql_schema: The GraphQL schema object to transform
        root_type: Optional root type name for the JSON schema

    Returns:
        Dict[str, Any]: JSON Schema representation
    """
    log.info("Starting GraphQL to JSON Schema transformation")

    json_schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": {},
    }

    if root_type:
        json_schema.update(
            {
                "title": root_type,
                "$ref": f"#/$defs/{root_type}",
            }
        )
    else:
        json_schema.update(
            {
                "type": "object",
                "title": "GraphQL Schema",
                "description": "JSON Schema generated from GraphQL schema",
            }
        )

    type_map = graphql_schema.type_map
    excluded_types = {"Query", "Mutation", "Subscription"}

    if root_type:
        referenced_types = get_referenced_types(graphql_schema, root_type)
        user_defined_types = {name: type_def for name, type_def in type_map.items() if name in referenced_types}
    else:
        user_defined_types = {
            name: type_def
            for name, type_def in type_map.items()
            if not name.startswith("__") and name not in excluded_types
        }

    log.info(f"Found {len(user_defined_types)} user-defined types to transform")

    for type_name, type_def in user_defined_types.items():
        try:
            json_schema_def = transform_graphql_type(type_def)
            if json_schema_def:
                json_schema["$defs"][type_name] = json_schema_def
                log.debug(f"Transformed type: {type_name}")
        except (AttributeError, TypeError, KeyError, ValueError) as e:
            log.error(f"Failed to transform type {type_name}: {e}")
            raise
        except Exception as e:
            log.error(f"Unexpected error transforming type {type_name}: {e}")
            raise

    log.info(f"Successfully transformed {len(json_schema['$defs'])} types")
    return json_schema


def transform_graphql_type(graphql_type: GraphQLType) -> dict[str, Any] | None:
    """
    Transform a single GraphQL type to JSON Schema definition.

    Args:
        graphql_type: The GraphQL type to transform

    Returns:
        Optional[Dict[str, Any]]: JSON Schema definition or None if not transformable
    """
    if is_scalar_type(graphql_type):
        return transform_scalar_type(cast(GraphQLScalarType, graphql_type))
    elif is_object_type(graphql_type):
        return transform_object_type(cast(GraphQLObjectType, graphql_type))
    elif is_enum_type(graphql_type):
        return transform_enum_type(cast(GraphQLEnumType, graphql_type))
    elif is_interface_type(graphql_type):
        return transform_interface_type(cast(GraphQLInterfaceType, graphql_type))
    elif is_union_type(graphql_type):
        return transform_union_type(cast(GraphQLUnionType, graphql_type))
    else:
        log.warning(f"Unsupported GraphQL type: {type(graphql_type)}")
        return None


def transform_scalar_type(scalar_type: GraphQLScalarType) -> dict[str, Any]:
    """
    Transform a GraphQL scalar type to JSON Schema.

    Args:
        scalar_type: The GraphQL scalar type

    Returns:
        Dict[str, Any]: JSON Schema definition
    """
    json_type = GRAPHQL_SCALAR_TO_JSON_SCHEMA.get(scalar_type.name, "string")

    definition = {
        "type": json_type,
    }

    if scalar_type.description:
        definition["description"] = scalar_type.description

    return definition


def transform_object_type(object_type: GraphQLObjectType) -> dict[str, Any]:
    """
    Transform a GraphQL object type to JSON Schema.

    Args:
        object_type: The GraphQL object type

    Returns:
        Dict[str, Any]: JSON Schema definition
    """
    definition: dict[str, Any] = {
        "type": "object",
        "properties": {},
    }

    if object_type.description:
        definition["description"] = object_type.description

    # Process directives
    if hasattr(object_type, "ast_node") and object_type.ast_node and object_type.ast_node.directives:
        directive_extensions = process_directives(list(object_type.ast_node.directives))
        definition.update(directive_extensions)

    # Process fields
    for field_name, field in object_type.fields.items():
        field_definition = transform_field(field)
        definition["properties"][field_name] = field_definition

    return definition


def transform_field(field: GraphQLField) -> dict[str, Any]:
    """
    Transform a GraphQL field to JSON Schema property.

    Args:
        field: The GraphQL field

    Returns:
        Dict[str, Any]: JSON Schema property definition
    """
    field_type = field.type
    definition = get_field_type_definition(field_type)

    if field.description:
        definition["description"] = field.description

    # Process field directives
    if hasattr(field, "ast_node") and field.ast_node and field.ast_node.directives:
        directive_extensions = process_directives(list(field.ast_node.directives))
        definition.update(directive_extensions)

    return definition


def get_field_type_definition(field_type: GraphQLType) -> dict[str, Any]:
    """
    Get JSON Schema definition for a GraphQL field type.

    Args:
        field_type: The GraphQL field type

    Returns:
        Dict[str, Any]: JSON Schema type definition
    """
    # Handle NonNull wrapper. e.g. `Type!`
    if is_non_null_type(field_type):
        return get_field_type_definition(cast(GraphQLNonNull[Any], field_type).of_type)

    # Handle List wrapper
    if is_list_type(field_type):
        list_type = cast(GraphQLList[Any], field_type)
        item_definition = get_field_type_definition(list_type.of_type)

        # Check if the list items are nullable (not wrapped in NonNull). e.g. `[Type]`
        # This handles cases like [Type] where items can be null: [Type, null, Type, ...]
        if not is_non_null_type(list_type.of_type):
            # For nullable items, allow the item type or null
            if "$ref" in item_definition:
                # For object/union references, use oneOf
                item_definition = {"oneOf": [item_definition, {"type": "null"}]}
            elif "type" in item_definition:
                # For primitive types, add null to the possible types array
                current_type = item_definition["type"]
                if isinstance(current_type, str):
                    item_definition["type"] = [current_type, "null"]
                elif isinstance(current_type, list) and "null" not in current_type:
                    item_definition["type"] = current_type + ["null"]

        return {"type": "array", "items": item_definition}

    # Handle scalar types
    if is_scalar_type(field_type):
        scalar_type = cast(GraphQLScalarType, field_type)
        json_type = GRAPHQL_SCALAR_TO_JSON_SCHEMA.get(scalar_type.name, "string")
        return {"type": json_type}

    # Handle enum types
    if is_enum_type(field_type):
        enum_type = cast(GraphQLEnumType, field_type)
        return {"$ref": f"#/$defs/{enum_type.name}"}

    # Handle object types (references)
    if is_object_type(field_type) or is_interface_type(field_type):
        named_type = cast(GraphQLObjectType | GraphQLInterfaceType, field_type)
        return {"$ref": f"#/$defs/{named_type.name}"}

    # Handle union types
    if is_union_type(field_type):
        union_type = cast(GraphQLUnionType, field_type)
        return {"$ref": f"#/$defs/{union_type.name}"}

    return {"type": "string"}


def process_directives(directives: list[Any]) -> dict[str, Any]:
    """
    Process GraphQL directives and convert them to JSON Schema extensions.

    Args:
        directives: List of GraphQL directive nodes

    Returns:
        Dict[str, Any]: JSON Schema extensions for the directives
    """
    extensions = {}

    for directive in directives:
        directive_name = directive.name.value

        if directive_name == "cardinality":
            args = get_directive_arguments(directive)
            if "min" in args:
                extensions["minItems"] = args["min"]
            if "max" in args:
                extensions["maxItems"] = args["max"]

        elif directive_name == "noDuplicates":
            extensions["uniqueItems"] = True

        elif directive_name == "range":
            args = get_directive_arguments(directive)
            if "min" in args:
                extensions["minimum"] = args["min"]
            if "max" in args:
                extensions["maximum"] = args["max"]

        else:
            """
            All other custom directives are included as an `x-` prefixed directive.

            Directives with arguments are stored as an object, while those without
            arguments are stored as a boolean.
            """
            args = get_directive_arguments(directive)
            if args:
                extensions[f"x-{directive_name}"] = args
            else:
                extensions[f"x-{directive_name}"] = True

    return extensions


def get_directive_arguments(directive: Any) -> dict[str, Any]:
    """
    Extract arguments from a GraphQL directive.

    Args:
        directive: GraphQL directive node

    Returns:
        Dict[str, Any]: Dictionary of argument names to values
    """
    args: dict[str, Any] = {}

    if hasattr(directive, "arguments") and directive.arguments:
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


def transform_enum_type(enum_type: GraphQLEnumType) -> dict[str, Any]:
    """
    Transform a GraphQL enum type to JSON Schema.

    Args:
        enum_type: The GraphQL enum type

    Returns:
        Dict[str, Any]: JSON Schema definition
    """
    enum_values = []
    for value in enum_type.values:
        # Handle enum values which might be strings or objects with .name attribute
        if hasattr(value, "name"):
            enum_values.append(value.name)
        else:
            enum_values.append(str(value))

    definition = {
        "type": "string",
        "enum": enum_values,
    }

    if enum_type.description:
        definition["description"] = enum_type.description

    return definition


def transform_interface_type(interface_type: GraphQLInterfaceType) -> dict[str, Any]:
    """
    Transform a GraphQL interface type to JSON Schema.

    Args:
        interface_type: The GraphQL interface type

    Returns:
        Dict[str, Any]: JSON Schema definition
    """
    definition: dict[str, Any] = {
        "type": "object",
        "properties": {},
    }

    if interface_type.description:
        definition["description"] = interface_type.description

    for field_name, field in interface_type.fields.items():
        field_definition = transform_field(field)
        definition["properties"][field_name] = field_definition

    return definition


def transform_union_type(union_type: GraphQLUnionType) -> dict[str, Any]:
    """
    Transform a GraphQL union type to JSON Schema.

    Args:
        union_type: The GraphQL union type

    Returns:
        Dict[str, Any]: JSON Schema definition
    """
    definition: dict[str, Any] = {
        "oneOf": [{"$ref": f"#/$defs/{member_type.name}"} for member_type in union_type.types],
    }

    if union_type.description:
        definition["description"] = union_type.description

    return definition
