from graphql import GraphQLField, GraphQLScalarType

from s2dm.exporters.utils.directive import get_directive_arguments, has_given_directive

INT32_MIN = -(2**31)
INT32_MAX = 2**31 - 1

GRAPHQL_SCALAR_TO_AVRO = {
    "String": "string",
    "Int": "int",
    "Float": "double",
    "Boolean": "boolean",
    "ID": "string",
    "Int8": "int",
    "UInt8": "int",
    "Int16": "int",
    "UInt16": "int",
    "UInt32": "long",
    "Int64": "long",
    "UInt64": "long",
}


def get_avro_scalar_type(scalar_type: GraphQLScalarType, field: GraphQLField | None = None) -> str:
    """Get Avro type for a GraphQL scalar, considering @range directive."""
    base_type = GRAPHQL_SCALAR_TO_AVRO.get(scalar_type.name, "string")

    if field and base_type in ("int", "long") and has_given_directive(field, "range"):
        range_args = get_directive_arguments(field, "range")

        for key in ("min", "max"):
            if key in range_args:
                val = range_args[key]
                if val < INT32_MIN or val > INT32_MAX:
                    return "long"

        return "int"

    return base_type
