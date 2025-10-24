from graphql import GraphQLNamedType, GraphQLObjectType, GraphQLSchema

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
