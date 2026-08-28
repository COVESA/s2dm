import inflect
from graphql import (
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLSchema,
)

from s2dm.exporters.utils.field import FieldCase, get_field_case
from s2dm.exporters.utils.graphql_type import is_introspection_type
from s2dm.exporters.utils.naming import TYPE_CONTEXTS, collect_instance_tag_enum_names, convert_name
from s2dm.exporters.utils.naming_config import (
    CaseFormat,
    ContextType,
    ElementType,
    NamingConventionConfig,
    get_case_for_element,
)

_inflect_engine = inflect.engine()


def _matches_case_format(
    name: str, case_format: CaseFormat, exceptions: dict[str, str] | None = None
) -> tuple[bool, str]:
    """Check if a name matches the specified case format.

    Args:
        name: The name to check
        case_format: The expected case format
        exceptions: Optional mapping of literal names to literal replacements that are
            considered compliant as-is, checked before case conversion.

    Returns:
        True if the name matches the case format, False otherwise
    """
    converted_name = convert_name(name, case_format, exceptions)
    matches = name == converted_name

    return matches, converted_name


def _is_plural(name: str) -> bool:
    """Check if a name is in plural form using inflect library.

    Args:
        name: The name to check

    Returns:
        True if the name is plural, False otherwise
    """
    singular = _inflect_engine.singular_noun(name)
    return singular is not False


def check_naming_conventions(
    schema: GraphQLSchema,
    config: NamingConventionConfig,
) -> list[str]:
    """Check all naming conventions for the schema.

    Args:
        schema: The GraphQL schema
        config: The naming convention configuration

    Returns:
        List of error messages for violations
    """
    type_errors = []
    field_errors = []
    argument_errors = []
    enum_value_errors = []
    plural_errors = []
    instance_tag_enum_names = collect_instance_tag_enum_names(schema)

    for type_name, object_type in schema.type_map.items():
        if is_introspection_type(type_name):
            continue

        context = TYPE_CONTEXTS.get(type(object_type))

        if not context:
            continue

        expected_case = get_case_for_element(ElementType.TYPE, context, config)
        if expected_case:
            matches, suggestion = _matches_case_format(type_name, expected_case, config.exceptions)
            if not matches:
                type_errors.append(
                    f"[naming] Type '{type_name}' should be {expected_case.value} (suggestion: '{suggestion}')"
                )

        if isinstance(object_type, GraphQLEnumType):
            enum_element_type = (
                ElementType.INSTANCE_TAG if type_name in instance_tag_enum_names else ElementType.ENUM_VALUE
            )
            expected_case = get_case_for_element(enum_element_type, None, config)
            if expected_case:
                for value_name in object_type.values:
                    matches, suggestion = _matches_case_format(value_name, expected_case, config.exceptions)
                    if not matches:
                        enum_value_errors.append(
                            f"[naming] Enum value '{object_type.name}.{value_name}' should be {expected_case.value} "
                            f"(suggestion: '{suggestion}')"
                        )

        if isinstance(object_type, GraphQLObjectType | GraphQLInterfaceType | GraphQLInputObjectType):
            field_case = get_case_for_element(ElementType.FIELD, context, config)
            argument_case = (
                get_case_for_element(ElementType.ARGUMENT, ContextType.FIELD, config)
                if isinstance(object_type, GraphQLObjectType | GraphQLInterfaceType)
                else None
            )

            for field_name, field in object_type.fields.items():
                if field_case:
                    matches, suggestion = _matches_case_format(field_name, field_case, config.exceptions)
                    if not matches:
                        field_errors.append(
                            f"[naming] Field '{object_type.name}.{field_name}' should be {field_case.value} "
                            f"(suggestion: '{suggestion}')"
                        )

                field_case_value = get_field_case(field)
                if (
                    isinstance(object_type, GraphQLObjectType | GraphQLInterfaceType)
                    and field_case_value
                    not in (
                        FieldCase.DEFAULT,
                        FieldCase.NON_NULL,
                    )
                    and not _is_plural(field_name)
                ):
                    suggestion = _inflect_engine.plural(field_name)
                    plural_errors.append(
                        f"[naming] List field '{object_type.name}.{field_name}' should be plural "
                        f"(suggestion: '{suggestion}')"
                    )

                if argument_case and field.args:
                    for arg_name in field.args:
                        matches, suggestion = _matches_case_format(arg_name, argument_case, config.exceptions)
                        if not matches:
                            argument_errors.append(
                                f"[naming] Argument '{object_type.name}.{field_name}({arg_name})' should be "
                                f"{argument_case.value} (suggestion: '{suggestion}')"
                            )

    return type_errors + field_errors + argument_errors + enum_value_errors + plural_errors
