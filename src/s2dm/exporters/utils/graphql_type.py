def is_introspection_type(type_name: str) -> bool:
    return type_name.startswith("__")


def is_root_type(type_name: str) -> bool:
    return type_name in {
        "Query",
        "Mutation",
        "Subscription",
    }


def is_introspection_or_root_type(type_name: str) -> bool:
    return is_introspection_type(type_name) or is_root_type(type_name)


def is_id_type(type_name: str) -> bool:
    return type_name == "ID"


def is_builtin_scalar_type(type_name: str) -> bool:
    return type_name in {
        "ID",
        "String",
        "Int",
        "Float",
        "Boolean",
    }


def is_graphql_system_type(type_name: str) -> bool:
    return is_introspection_or_root_type(type_name) or is_builtin_scalar_type(type_name)
