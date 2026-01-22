from typing import Any

from graphql import GraphQLSchema

from s2dm.exporters.utils.graphql_type import is_introspection_type


def search_schema(
    schema: GraphQLSchema,
    type_name: str | None = None,
    field_name: str | None = None,
    partial: bool = False,
    case_insensitive: bool = False,
) -> dict[str, list[Any] | None]:
    """
    Search for types and/or fields in a GraphQL schema.

    Args:
        schema (GraphQLSchema): The schema to search.
        type_name (str, optional): The name (or partial name) of the type to search for.
        field_name (str, optional): The name (or partial name) of the field to search for within the type(s).
        partial (bool): If True, allows partial (substring) matches for type and field names.
        case_insensitive (bool): If True, search is case-insensitive.

    Returns:
        dict: {type_name: [field_names]} for matches, or just type names if field_name is None.
    """
    results: dict[str, list[Any] | None] = {}
    for tname, t in schema.type_map.items():
        if is_introspection_type(tname):
            continue
        tname_cmp = tname.lower() if case_insensitive else tname
        type_name_cmp = type_name.lower() if (type_name and case_insensitive) else type_name
        type_match = (
            type_name is None
            or (partial and type_name_cmp is not None and type_name_cmp in tname_cmp)
            or (not partial and type_name_cmp is not None and tname_cmp == type_name_cmp)
        )
        if type_match:
            fields = getattr(t, "fields", None)
            if callable(fields):
                fields = fields()
            if isinstance(fields, dict):
                if field_name:
                    field_name_cmp = field_name.lower() if case_insensitive else field_name
                    matched_fields = [
                        fname
                        for fname in fields
                        if (partial and field_name_cmp in (fname.lower() if case_insensitive else fname))
                        or (not partial and (fname.lower() if case_insensitive else fname) == field_name_cmp)
                    ]
                    if matched_fields:
                        results[tname] = matched_fields
                else:
                    results[tname] = list(fields)
            else:
                continue

    return results
