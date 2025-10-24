from typing import Any, cast

from graphql import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNamedType,
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
from s2dm.exporters.utils.instance_tag import expand_instance_tag, get_instance_tag_object, is_valid_instance_tag_field
from s2dm.exporters.utils.schema_loader import get_referenced_types

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
        expanded_instances: bool = False,
        naming_config: dict[str, Any] | None = None,
    ):
        self.graphql_schema = graphql_schema
        self.root_type = root_type
        self.strict = strict
        self.expanded_instances = expanded_instances
        self.naming_config = naming_config

    def transform(self) -> dict[str, Any]:
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

        if self.root_type:
            referenced_types = get_referenced_types(self.graphql_schema, self.root_type)
            user_defined_types: list[GraphQLNamedType] = [
                t for t in referenced_types if isinstance(t, GraphQLNamedType)
            ]
        else:
            user_defined_types = get_all_named_types(self.graphql_schema)

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
            directive_extensions = self.process_directives(object_type)
            definition.update(directive_extensions)

        required_fields = []
        for field_name, field in object_type.fields.items():
            if is_valid_instance_tag_field(field, self.graphql_schema):
                if field_name == "instanceTag":
                    # Skip instanceTag field as it is handled separately
                    continue
                else:
                    # Fields with an instanceTag object type should not be allowed since object
                    # types with @instanceTag directives are not included in the JSON schema.
                    raise ValueError(
                        f"Invalid schema: instanceTag object found on non-instanceTag named field '{field_name}'"
                    )

            if is_non_null_type(field.type):
                required_fields.append(field_name)

            field_definition = self.transform_field(field)

            # Handle the case where field_definition might be a tuple (for expanded instances)
            property_name = field_name
            if isinstance(field_definition, tuple):
                field_definition, singular_name = field_definition
                property_name = singular_name

            definition["properties"][property_name] = field_definition

        if required_fields:
            definition["required"] = required_fields

        return definition

    def transform_field(self, field: GraphQLField) -> dict[str, Any] | tuple[dict[str, Any], str]:
        """
        Transform a GraphQL field to JSON Schema property.

        Args:
            field: The GraphQL field

        Returns:
            JSON Schema property definition, or tuple of (definition, singular_name) for expanded instances
        """
        field_type = field.type
        definition = self.get_field_type_definition(field_type)

        # Handle the case where definition might be a tuple (for expanded instances)
        singular_name = None
        if isinstance(definition, tuple):
            definition, singular_name = definition

        if field.description:
            definition["description"] = field.description

        # Process field directives
        if hasattr(field, "ast_node") and field.ast_node and field.ast_node.directives:
            directive_extensions = self.process_directives(field)
            # For expanded instances (when we return a tuple), don't apply array-specific directives
            if singular_name is not None:
                # Remove array-specific directives for expanded instances since they become objects
                directive_extensions.pop("uniqueItems", None)
                directive_extensions.pop("minItems", None)
                directive_extensions.pop("maxItems", None)
            definition.update(directive_extensions)

        if singular_name:
            return (definition, singular_name)
        return definition

    def get_field_type_definition(
        self, field_type: GraphQLType, nullable: bool = True
    ) -> dict[str, Any] | tuple[dict[str, Any], str]:
        """
        Get JSON Schema definition for a GraphQL field type.

        Args:
            field_type: The GraphQL field type
            nullable: Whether the field is nullable (not wrapped in NonNull)

        Returns:
            JSON Schema type definition, or tuple of (definition, singular_name) for expanded instances
        """
        # Handle NonNull wrapper. e.g. `Type!`
        if is_non_null_type(field_type):
            return self.get_field_type_definition(cast(GraphQLNonNull[Any], field_type).of_type, nullable=False)

        # Handle List wrapper
        if is_list_type(field_type):
            list_type = cast(GraphQLList[Any], field_type)

            # Check if we should expand instances and if list contains objects with instance tags
            if self.expanded_instances:
                # Get the actual item type (unwrap NonNull if present)
                item_type = list_type.of_type
                if is_non_null_type(item_type):
                    item_type = item_type.of_type

                # Check if the item type is an object with instance tags
                if is_object_type(item_type):
                    item_object_type = cast(GraphQLObjectType, item_type)
                    instance_tag_object = get_instance_tag_object(item_object_type, self.graphql_schema)
                    if instance_tag_object:
                        # Create expanded nested structure instead of array
                        expanded_def = self.create_expanded_instance_structure(item_object_type, instance_tag_object)
                        # Return both the definition and the singular type name
                        return (expanded_def, item_object_type.name)

            item_definition = self.get_field_type_definition(list_type.of_type)

            # Handle the case where item_definition might be a tuple (for nested expanded instances)
            if isinstance(item_definition, tuple):
                item_definition = item_definition[0]

            # Check if the list items are nullable (not wrapped in NonNull). e.g. `[Type]`
            # This handles cases like [Type] where items can be null: [Type, null, Type, ...]
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
            json_type = GRAPHQL_SCALAR_TO_JSON_SCHEMA.get(scalar_type.name, "string")
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

        if is_object_type(named_type):
            instance_tag_object = get_instance_tag_object(cast(GraphQLObjectType, named_type), self.graphql_schema)
            if instance_tag_object:
                expanded_instance_tag = expand_instance_tag(instance_tag_object, self.naming_config)

                definition: dict[str, Any] = {
                    "additionalProperties": False,
                    "properties": {},
                    "type": "object",
                }
                for expanded_instance in expanded_instance_tag:
                    current_definition = definition["properties"]
                    expanded_instance_split = expanded_instance.split(".")

                    for index, part in enumerate(expanded_instance_split):
                        is_last_split_element = index == len(expanded_instance_split) - 1

                        if part not in current_definition:
                            if is_last_split_element:
                                current_definition[part] = {}
                            else:
                                current_definition[part] = {
                                    "additionalProperties": False,
                                    "properties": {},
                                    "type": "object",
                                }

                        if is_last_split_element:
                            current_definition = current_definition[part]
                        else:
                            current_definition = current_definition[part]["properties"]

                    current_definition["$ref"] = f"#/$defs/{named_type.name}"
                return definition

        return {"$ref": f"#/$defs/{named_type.name}"}

    def create_expanded_instance_structure(
        self, object_type: GraphQLObjectType, instance_tag_object: GraphQLObjectType
    ) -> dict[str, Any]:
        """
        Create an expanded nested structure for objects with instance tags instead of arrays.

        Args:
            object_type: The GraphQL object type that contains the instance tag
            instance_tag_object: The instance tag object type

        Returns:
            Dict[str, Any]: JSON Schema definition with expanded nested structure
        """
        expanded_instance_tags = expand_instance_tag(instance_tag_object, self.naming_config)

        definition: dict[str, Any] = {
            "additionalProperties": False,
            "properties": {},
            "type": "object",
        }

        for expanded_instance in expanded_instance_tags:
            current_definition = definition["properties"]
            expanded_instance_split = expanded_instance.split(".")

            for index, part in enumerate(expanded_instance_split):
                is_last_split_element = index == len(expanded_instance_split) - 1

                if part not in current_definition:
                    if is_last_split_element:
                        # For the last element, use a reference to the object type
                        current_definition[part] = {"$ref": f"#/$defs/{object_type.name}"}
                    else:
                        current_definition[part] = {
                            "additionalProperties": False,
                            "properties": {},
                            "type": "object",
                        }

                if not is_last_split_element:
                    current_definition = current_definition[part]["properties"]

        return definition

    def process_directives(self, element: GraphQLField | GraphQLObjectType) -> dict[str, Any]:
        """
        Process GraphQL directives and convert them to JSON Schema extensions.

        Args:
            directives: List of GraphQL directive nodes

        Returns:
            Dict[str, Any]: JSON Schema extensions for the directives
        """
        extensions: dict[str, Any] = {}

        if has_given_directive(element, "noDuplicates"):
            extensions["uniqueItems"] = True

        if isinstance(element, GraphQLField):
            cardinality = get_cardinality(element)
            if cardinality:
                if cardinality.min is not None:
                    extensions["minItems"] = cardinality.min
                if cardinality.max is not None:
                    extensions["maxItems"] = cardinality.max

        if has_given_directive(element, "range"):
            args = get_directive_arguments(element, "range")
            if "min" in args:
                extensions["minimum"] = args["min"]
            if "max" in args:
                extensions["maximum"] = args["max"]

        if has_given_directive(element, "metadata"):
            args = get_directive_arguments(element, "metadata")
            if "comment" in args:
                extensions["$comment"] = args["comment"]
            other_metadata = {k: v for k, v in args.items() if k != "comment"}
            if other_metadata:
                extensions["x-metadata"] = other_metadata

        return extensions

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
