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

from s2dm import log
from s2dm.exporters.utils.directive import get_directive_arguments, has_given_directive
from s2dm.exporters.utils.extraction import get_all_named_types
from s2dm.exporters.utils.field import get_cardinality
from s2dm.exporters.utils.instance_tag import (
    is_instance_tag_field,
    is_valid_instance_tag_field,
)

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


class JsonSchemaTransformer:
    """
    Transformer class to convert GraphQL schema to JSON Schema format.

    This class provides methods to transform various GraphQL types into their
    corresponding JSON Schema definitions, handling directives and nested types.
    """

    def __init__(
        self,
        graphql_schema: GraphQLSchema,
        root_type: str | None = None,
        strict: bool = False,
    ):
        self.graphql_schema = graphql_schema
        self.root_type = root_type
        self.strict = strict

    def transform(self) -> dict[str, Any]:
        """
        Transform a GraphQL schema to JSON Schema format.

        Converts all GraphQL types (except Query/Mutation/Subscription) into JSON Schema
        definitions in the $defs section. Handles directives as well.

        Returns:
            Dict[str, Any]: JSON Schema representation
        """
        log.info("Starting GraphQL to JSON Schema transformation")

        json_schema: dict[str, Any] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": {},
        }

        if self.root_type:
            json_schema.update(
                {
                    "title": self.root_type,
                    "$ref": f"#/$defs/{self.root_type}",
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

        all_types = get_all_named_types(self.graphql_schema)
        user_defined_types = [graphql_type for graphql_type in all_types if not is_scalar_type(graphql_type)]

        log.info(f"Found {len(user_defined_types)} user-defined types to transform")

        for type_def in user_defined_types:
            type_name = type_def.name
            try:
                json_schema_def = self.transform_graphql_type(type_def)
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

    def transform_graphql_type(self, graphql_type: GraphQLType) -> dict[str, Any] | None:
        """
        Transform a single GraphQL type to JSON Schema definition.

        Args:
            graphql_type: The GraphQL type to transform

        Returns:
            Optional[Dict[str, Any]]: JSON Schema definition or None if not transformable
        """
        if is_object_type(graphql_type) and not has_given_directive(
            cast(GraphQLObjectType, graphql_type), "instanceTag"
        ):
            return self.transform_object_type(cast(GraphQLObjectType, graphql_type))
        elif is_object_type(graphql_type) and has_given_directive(cast(GraphQLObjectType, graphql_type), "instanceTag"):
            object_type = cast(GraphQLObjectType, graphql_type)
            log.warning(f"Skipping object type with @instanceTag directive: {object_type.name}")
            return None
        elif is_enum_type(graphql_type):
            return self.transform_enum_type(cast(GraphQLEnumType, graphql_type))
        elif is_interface_type(graphql_type):
            return self.transform_interface_type(cast(GraphQLInterfaceType, graphql_type))
        elif is_union_type(graphql_type):
            return self.transform_union_type(cast(GraphQLUnionType, graphql_type))
        else:
            log.warning(
                f"Unsupported GraphQL type: {type(graphql_type)} found in element {graphql_type} of the given schema"
            )
            return None

    def transform_object_type(self, object_type: GraphQLObjectType) -> dict[str, Any]:
        """
        Transform a GraphQL object type to JSON Schema.

        Args:
            object_type: The GraphQL object type

        Returns:
            Dict[str, Any]: JSON Schema definition
        """
        definition: dict[str, Any] = {
            "additionalProperties": False,
            "properties": {},
            "type": "object",
        }

        if object_type.description:
            definition["description"] = object_type.description

        # Process directives
        if hasattr(object_type, "ast_node") and object_type.ast_node and object_type.ast_node.directives:
            directive_result = self.process_directives(object_type)
            definition.update(directive_result["field"])

        required_fields = []
        for field_name, field in object_type.fields.items():
            if is_valid_instance_tag_field(field, self.graphql_schema):
                if is_instance_tag_field(field_name):
                    continue
                else:
                    raise ValueError(
                        f"Invalid schema: instanceTag object found on non-instanceTag named field '{field_name}'"
                    )

            if is_non_null_type(field.type):
                required_fields.append(field_name)

            field_definition = self.transform_field(field)
            definition["properties"][field_name] = field_definition

        if required_fields:
            definition["required"] = required_fields

        return definition

    def transform_field(self, field: GraphQLField) -> dict[str, Any]:
        """
        Transform a GraphQL field to JSON Schema property.

        Args:
            field: The GraphQL field

        Returns:
            JSON Schema property definition
        """
        field_type = field.type
        definition = self.get_field_type_definition(field_type)

        if field.description:
            definition["description"] = field.description

        if hasattr(field, "ast_node") and field.ast_node and field.ast_node.directives:
            directive_result = self.process_directives(field, field_type)
            field_directives = directive_result["field"]
            contained_type_directives = directive_result["contained_type"]

            definition.update(field_directives)
            if contained_type_directives and definition.get("type") == "array" and "items" in definition:
                definition["items"].update(contained_type_directives)

        return definition

    def get_field_type_definition(self, field_type: GraphQLType, nullable: bool = True) -> dict[str, Any]:
        """
        Get JSON Schema definition for a GraphQL field type.

        Args:
            field_type: The GraphQL field type
            nullable: Whether the field is nullable (not wrapped in NonNull)

        Returns:
            JSON Schema type definition
        """
        definition: dict[str, Any] = {}

        # Handle NonNull wrapper. e.g. `Type!`
        if is_non_null_type(field_type):
            return self.get_field_type_definition(cast(GraphQLNonNull[Any], field_type).of_type, nullable=False)

        # Handle List wrapper
        if is_list_type(field_type):
            list_type = cast(GraphQLList[Any], field_type)
            item_definition = self.get_field_type_definition(list_type.of_type)

            if not is_non_null_type(list_type.of_type) and self.strict:
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

            definition = {"type": "array", "items": item_definition}

            if nullable and self.strict:
                return {"oneOf": [definition, {"type": "null"}]}

            return definition

        # Handle scalar types
        if is_scalar_type(field_type):
            scalar_type = cast(GraphQLScalarType, field_type)
            json_type = GRAPHQL_SCALAR_TO_JSON_SCHEMA.get(scalar_type.name)
            if json_type:
                definition = {"type": json_type}

            if nullable and self.strict:
                definition = {"type": [json_type, "null"]}

            return definition

        # Handle enum types
        if is_enum_type(field_type):
            enum_type = cast(GraphQLEnumType, field_type)
            definition = {"$ref": f"#/$defs/{enum_type.name}"}

            if nullable and self.strict:
                return {"oneOf": [definition, {"type": "null"}]}

            return definition

        # Handle object types (references)
        if is_object_type(field_type) or is_interface_type(field_type):
            definition = self.process_field_object_type(field_type)

            if nullable and self.strict:
                return {"oneOf": [definition, {"type": "null"}]}

            return definition

        # Handle union types
        if is_union_type(field_type):
            union_type = cast(GraphQLUnionType, field_type)
            definition = {"$ref": f"#/$defs/{union_type.name}"}

            if nullable and self.strict:
                return {"oneOf": [definition, {"type": "null"}]}

            return definition

        return {"type": "string"}

    def process_field_object_type(self, field_type: GraphQLType) -> dict[str, Any]:
        """
        Process a GraphQL field type that is an object type.

        Args:
            field_type: The GraphQL field type

        Returns:
            Dict[str, Any]: JSON Schema definition for the object type
        """
        named_type = cast(GraphQLObjectType | GraphQLInterfaceType, field_type)
        return {"$ref": f"#/$defs/{named_type.name}"}

    def process_directives(
        self, element: GraphQLField | GraphQLObjectType, field_type: GraphQLType | None = None
    ) -> dict[str, Any]:
        """
        Process GraphQL directives and convert them to JSON Schema extensions.

        Args:
            element: The GraphQL field or object type with directives
            field_type: The GraphQL type of the field (for context-aware processing)

        Returns:
            Dict with 'field' and 'contained_type' keys for directives that apply to
            the field itself vs the contained type (items in arrays, members in unions, etc.)
        """
        field_extensions: dict[str, Any] = {}
        contained_type_extensions: dict[str, Any] = {}

        if has_given_directive(element, "noDuplicates"):
            field_extensions["uniqueItems"] = True

        if isinstance(element, GraphQLField):
            cardinality = get_cardinality(element)
            if cardinality:
                if cardinality.min is not None:
                    field_extensions["minItems"] = cardinality.min
                if cardinality.max is not None:
                    field_extensions["maxItems"] = cardinality.max

        if has_given_directive(element, "range"):
            args = get_directive_arguments(element, "range")
            range_extensions = {}
            if "min" in args:
                range_extensions["minimum"] = args["min"]
            if "max" in args:
                range_extensions["maximum"] = args["max"]

            unwrapped_type = field_type
            if unwrapped_type and is_non_null_type(unwrapped_type):
                unwrapped_type = cast(GraphQLNonNull[Any], unwrapped_type).of_type

            if unwrapped_type and is_list_type(unwrapped_type):
                contained_type_extensions.update(range_extensions)
            else:
                field_extensions.update(range_extensions)

        if has_given_directive(element, "metadata"):
            args = get_directive_arguments(element, "metadata")
            if "comment" in args:
                field_extensions["$comment"] = args["comment"]
            other_metadata = {k: v for k, v in args.items() if k != "comment"}
            if other_metadata:
                field_extensions["x-metadata"] = other_metadata

        return {"field": field_extensions, "contained_type": contained_type_extensions}

    def transform_enum_type(self, enum_type: GraphQLEnumType) -> dict[str, Any]:
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

    def transform_interface_type(self, interface_type: GraphQLInterfaceType) -> dict[str, Any]:
        """
        Transform a GraphQL interface type to JSON Schema.

        Args:
            interface_type: The GraphQL interface type

        Returns:
            Dict[str, Any]: JSON Schema definition
        """
        definition: dict[str, Any] = {
            "additionalProperties": False,
            "properties": {},
            "type": "object",
        }

        if interface_type.description:
            definition["description"] = interface_type.description

        required_fields = []
        for field_name, field in interface_type.fields.items():
            if is_non_null_type(field.type):
                required_fields.append(field_name)

            field_definition = self.transform_field(field)
            definition["properties"][field_name] = field_definition

        if required_fields:
            definition["required"] = required_fields

        return definition

    def transform_union_type(self, union_type: GraphQLUnionType) -> dict[str, Any]:
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
