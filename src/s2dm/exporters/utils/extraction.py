from graphql import (
    DocumentNode,
    FieldNode,
    GraphQLNamedType,
    GraphQLObjectType,
    GraphQLSchema,
    OperationDefinitionNode,
    OperationType,
    get_named_type,
    is_interface_type,
    is_object_type,
)

from s2dm.exporters.utils.directive import has_given_directive
from s2dm.exporters.utils.graphql_type import is_introspection_type


def get_all_named_types(schema: GraphQLSchema) -> list[GraphQLNamedType]:
    """
    Extracts all named types (ScalarType, ObjectType, InterfaceType, UnionType, EnumType, and InputObjectType)
    from the provided GraphQL schema.

    Args:
        schema (GraphQLSchema): The GraphQL schema to extract named types from.
    Returns:
        list[GraphQLNamedType]: A list of all named types in the schema.
    """
    return [type_ for type_ in schema.type_map.values() if not is_introspection_type(type_.name)]


def get_all_object_types(
    schema: GraphQLSchema,
) -> list[GraphQLObjectType]:
    """
    Extracts all object types from the provided GraphQL schema.
    Args:
        schema (GraphQLSchema): The GraphQL schema to extract object types from.
    Returns:
        list[GraphQLObjectType]: A list of all object types in the schema.
    """
    named_types = get_all_named_types(schema)
    return [type_ for type_ in named_types if isinstance(type_, GraphQLObjectType)]


def get_all_objects_with_directive(objects: list[GraphQLObjectType], directive_name: str) -> list[GraphQLObjectType]:
    # TODO: Extend this function to return all objects that have any directive is directive_name is None
    return [o for o in objects if has_given_directive(o, directive_name)]


def get_root_level_types_from_query(schema: GraphQLSchema, selection_query: DocumentNode | None) -> list[str]:
    """Extract root-level type names from the selection query.

    Args:
        schema: The GraphQL schema
        selection_query: The selection query document

    Returns:
        List of type names that are selected at the root level of the query
    """
    query_type = schema.query_type
    if not selection_query or not query_type:
        return []

    root_type_names: list[str] = []

    for definition in selection_query.definitions:
        if not isinstance(definition, OperationDefinitionNode) or definition.operation != OperationType.QUERY:
            continue

        for selection in definition.selection_set.selections:
            if not isinstance(selection, FieldNode):
                continue

            field_name = selection.name.value
            if field_name not in query_type.fields:
                continue

            field = query_type.fields[field_name]
            field_type = get_named_type(field.type)

            if is_object_type(field_type) or is_interface_type(field_type):
                root_type_names.append(field_type.name)

    return root_type_names


def get_query_operation_name(selection_query: DocumentNode, default_name: str) -> str:
    """
    Extract the operation name from a selection query document.

    Args:
        selection_query: The GraphQL selection query document
        default_name: Default name to use if no operation name is found

    Returns:
        str: The operation name from the query, or default_name if not found
    """
    for definition in selection_query.definitions:
        if not isinstance(definition, OperationDefinitionNode) or definition.operation != OperationType.QUERY:
            continue

        if definition.name:
            return definition.name.value
        return default_name

    return default_name
