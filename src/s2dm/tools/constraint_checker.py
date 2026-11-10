from graphql import (
    GraphQLEnumType,
    GraphQLInputObjectType,
    GraphQLInterfaceType,
    GraphQLObjectType,
    GraphQLSchema,
    get_named_type,
    get_nullable_type,
    is_list_type,
    validate_schema,
)
from graphql.language.ast import DirectiveNode, EnumValueNode

from s2dm.constants.directive import Directive, DirectiveArgument
from s2dm.exporters.utils.directive import (
    get_directive_arguments,
    get_field_with_applied_directive,
    get_objects_with_multiple_fields_with_directive,
    has_given_directive,
)
from s2dm.exporters.utils.instance_tag import (
    collect_expandable_fields,
    get_instance_tag_case,
    get_instance_tag_type,
    included_instances,
    is_instance_tag_field,
    resolve_instance_tag,
)
from s2dm.exporters.utils.naming_config import NamingConventionConfig
from s2dm.exporters.utils.violations import ConstraintCode, ConstraintViolation, Severity
from s2dm.tools.naming_checker import check_naming_conventions
from s2dm.utils.sequence import get_sequence_or_empty


def _get_invalid_directive_enum_argument_values(
    schema: GraphQLSchema, directive_node: DirectiveNode, context: str
) -> list[str]:
    """Find enum arguments in this directive usage whose value isn't defined by that enum."""
    errors: list[str] = []

    directive_definition = schema.get_directive(directive_node.name.value)
    if not directive_definition:
        return errors

    for argument_node in get_sequence_or_empty(directive_node.arguments):
        argument_name = argument_node.name.value
        argument_definition = directive_definition.args[argument_name]
        named_type = get_named_type(argument_definition.type)

        if not isinstance(named_type, GraphQLEnumType):
            continue

        if not isinstance(argument_node.value, EnumValueNode):
            continue

        enum_value = argument_node.value.value
        if enum_value not in named_type.values:
            errors.append(
                f"{context} uses directive '@{directive_node.name.value}({argument_name})' "
                f"with invalid enum value '{enum_value}'. Valid values are: {list(named_type.values.keys())}"
            )

    return errors


def get_directive_enum_value_errors(schema: GraphQLSchema) -> list[str]:
    """Check that the enum arguments of applied directives use values that exist in their enum definitions."""
    errors: list[str] = []

    for type_name, type_object in schema.type_map.items():
        if type_object.ast_node and type_object.ast_node.directives:
            for directive_node in type_object.ast_node.directives:
                errors.extend(
                    _get_invalid_directive_enum_argument_values(schema, directive_node, f"Type '{type_name}'")
                )

        if isinstance(type_object, GraphQLObjectType | GraphQLInterfaceType | GraphQLInputObjectType):
            for field_name, field in type_object.fields.items():
                if field.ast_node and field.ast_node.directives:
                    for directive_node in field.ast_node.directives:
                        errors.extend(
                            _get_invalid_directive_enum_argument_values(
                                schema, directive_node, f"Field '{type_name}.{field_name}'"
                            )
                        )

    return errors


class ConstraintChecker:
    def __init__(self, schema: GraphQLSchema, naming_config: NamingConventionConfig | None = None):
        self.schema = schema
        self.naming_config = naming_config

    def check_schema_spec(self) -> list[ConstraintViolation]:
        spec_errors = validate_schema(self.schema)
        return [ConstraintViolation(ConstraintCode.SCHEMA_SPEC, spec_error.message) for spec_error in spec_errors]

    def check_directive_enum_values(self) -> list[ConstraintViolation]:
        directive_enum_value_errors = get_directive_enum_value_errors(self.schema)
        return [
            ConstraintViolation(ConstraintCode.DIRECTIVE_ENUM_VALUE, error) for error in directive_enum_value_errors
        ]

    def check_min_not_greater_than_max(
        self, objects: list[GraphQLObjectType], directive: Directive
    ) -> list[ConstraintViolation]:
        violations: list[ConstraintViolation] = []
        for object_type in objects:
            for field_name, field in object_type.fields.items():
                if has_given_directive(field, directive):
                    arguments = get_directive_arguments(field, directive)
                    try:
                        min_value = arguments.get(DirectiveArgument.MIN)
                        max_value = arguments.get(DirectiveArgument.MAX)
                        if min_value is not None and max_value is not None and float(min_value) > float(max_value):
                            violations.append(
                                ConstraintViolation(
                                    ConstraintCode.MIN_GREATER_THAN_MAX,
                                    f"[{directive.value}] {object_type.name}.{field_name} has min > max "
                                    f"({min_value} > {max_value})",
                                )
                            )
                    except (ValueError, TypeError) as exc:
                        violations.append(
                            ConstraintViolation(
                                ConstraintCode.INVALID_MIN_MAX,
                                f"[{directive.value}] {object_type.name}.{field_name} has invalid min/max "
                                f"values: {exc}",
                            )
                        )

        return violations

    def check_instance_tag_expandability(self, objects: list[GraphQLObjectType]) -> list[ConstraintViolation]:
        violations: list[ConstraintViolation] = []
        for object_type in objects:
            for field_name, field in object_type.fields.items():
                base_type = get_named_type(field.type)
                if not isinstance(base_type, GraphQLObjectType):
                    continue

                resolved_instance_tag = resolve_instance_tag(base_type, self.schema)
                if resolved_instance_tag is None:
                    continue

                unwrapped_type = get_nullable_type(field.type)
                if is_list_type(unwrapped_type):
                    continue

                violations.append(
                    ConstraintViolation(
                        ConstraintCode.INSTANCE_TAG_NOT_EXPANDED,
                        f"[instanceTag] {object_type.name}.{field_name}: {base_type.name} has a valid expandable "
                        "output type but it is not expanded because it was not declared with the list "
                        "type modifier []",
                        severity=Severity.WARNING,
                    )
                )
        return violations

    def check_instance_tag_exclude_list(self) -> list[ConstraintViolation]:
        """Check that every @instanceTag exclude entry matches a real instance.

        `included_instances` raises `ValueError` when an exclude entry matches no instance; that
        exception is the signal this method turns into a violation, one per bad entry.
        """
        instance_tag_case = get_instance_tag_case(self.naming_config)
        expandable_fields = collect_expandable_fields(self.schema)
        violations: list[ConstraintViolation] = []
        for expandable in expandable_fields:
            try:
                included_instances(expandable, instance_tag_case)
            except ValueError as exc:
                violations.append(ConstraintViolation(ConstraintCode.INSTANCE_TAG_INVALID_EXCLUDE, str(exc)))
        return violations

    def check_instance_tag_source_type_fields(self, objects: list[GraphQLObjectType]) -> list[ConstraintViolation]:
        violations: list[ConstraintViolation] = []
        for object_type in objects:
            if not has_given_directive(object_type, Directive.INSTANCE_TAG):
                continue

            tagged_fields = get_field_with_applied_directive(object_type, Directive.INSTANCE_TAG)
            for field_name in tagged_fields:
                violations.append(
                    ConstraintViolation(
                        ConstraintCode.INSTANCE_TAG_SOURCE_FIELD_TAGGED,
                        f"[instanceTag] {object_type.name}.{field_name} must not be tagged with "
                        "@instanceTag (in @instanceTag object)",
                    )
                )

            for field_name, field in object_type.fields.items():
                field_type = get_named_type(field.type)
                if not isinstance(field_type, GraphQLEnumType):
                    violations.append(
                        ConstraintViolation(
                            ConstraintCode.INSTANCE_TAG_NON_ENUM_FIELD,
                            f"[instanceTag] {object_type.name}.{field_name} must be an enum (in @instanceTag object)",
                        )
                    )
        return violations

    def check_instance_tag_single_dimension(self, objects: list[GraphQLObjectType]) -> list[ConstraintViolation]:
        violations: list[ConstraintViolation] = []
        for object_type in objects:
            if not has_given_directive(object_type, Directive.INSTANCE_TAG) or len(object_type.fields) != 1:
                continue

            violations.append(
                ConstraintViolation(
                    ConstraintCode.INSTANCE_TAG_SINGLE_DIMENSION,
                    f"[instanceTag] type {object_type.name} @instanceTag has a single dimension. Consider "
                    f"using a direct enum instead: enum {object_type.name} @instanceTag",
                    severity=Severity.WARNING,
                )
            )
        return violations

    def check_instance_tag_reference(self, objects: list[GraphQLObjectType]) -> list[ConstraintViolation]:
        violations: list[ConstraintViolation] = []
        for object_type in objects:
            for field_name, field in object_type.fields.items():
                if not is_instance_tag_field(field):
                    continue

                output_type = get_instance_tag_type(field, self.schema)
                if output_type is None:
                    violations.append(
                        ConstraintViolation(
                            ConstraintCode.INSTANCE_TAG_INVALID_REFERENCE,
                            f"[instanceTag] {object_type.name}.{field_name} must reference an object or enum "
                            "type with @instanceTag",
                        )
                    )
        return violations

    def check_instance_tag_multiple_fields(self, objects: list[GraphQLObjectType]) -> list[ConstraintViolation]:
        violations: list[ConstraintViolation] = []
        objects_with_multiple_instance_tags = get_objects_with_multiple_fields_with_directive(
            objects, Directive.INSTANCE_TAG
        )
        for object_name, field_names in objects_with_multiple_instance_tags.items():
            joined = ", ".join(field_names)
            violations.append(
                ConstraintViolation(
                    ConstraintCode.INSTANCE_TAG_MULTIPLE_FIELDS,
                    f"[instanceTag] {object_name} must have at most one @instanceTag field (found: {joined})",
                )
            )
        return violations

    def run(self, objects: list[GraphQLObjectType]) -> list[ConstraintViolation]:
        """Run every constraint check and return all violations, errors and warnings alike."""
        violations: list[ConstraintViolation] = []
        violations += self.check_instance_tag_reference(objects)
        violations += self.check_instance_tag_multiple_fields(objects)
        violations += self.check_schema_spec()
        violations += self.check_directive_enum_values()
        violations += self.check_instance_tag_source_type_fields(objects)
        violations += self.check_instance_tag_expandability(objects)
        violations += self.check_instance_tag_single_dimension(objects)
        violations += self.check_instance_tag_exclude_list()
        violations += self.check_min_not_greater_than_max(objects, Directive.RANGE)
        violations += self.check_min_not_greater_than_max(objects, Directive.CARDINALITY)

        if self.naming_config:
            naming_errors = check_naming_conventions(self.schema, self.naming_config)
            violations += [ConstraintViolation(ConstraintCode.NAMING_CONVENTION, error) for error in naming_errors]

        return violations
