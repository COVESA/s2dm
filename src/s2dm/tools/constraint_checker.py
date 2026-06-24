from graphql import GraphQLEnumType, GraphQLObjectType, GraphQLSchema, get_named_type

from s2dm.exporters.utils.directive import get_directive_arguments, has_given_directive
from s2dm.exporters.utils.field import has_valid_cardinality
from s2dm.exporters.utils.naming_config import NamingConventionConfig
from s2dm.tools.naming_checker import check_naming_conventions


class ConstraintChecker:
    def __init__(self, schema: GraphQLSchema, naming_config: NamingConventionConfig | None = None):
        self.schema = schema
        self.naming_config = naming_config

    def check_cardinality_on_list_only(self, objects: list[GraphQLObjectType]) -> list[str]:
        """Flag @cardinality applied to non-list fields.

        @cardinality(min, max) describes the size of a list. On a scalar field the
        size is already fixed by the GraphQL type itself (T is 0..1, T! is 1..1),
        so any @cardinality annotation is redundant or contradicts the GraphQL
        non-null markers.
        """
        errors = []
        for obj in objects:
            for fname, field in obj.fields.items():
                if has_given_directive(field, "cardinality") and not has_valid_cardinality(field):
                    errors.append(
                        f"[cardinality] {obj.name}.{fname} has @cardinality on a non-list "
                        f"type ({field.type}); cardinality only applies to list-typed fields."
                    )
        return errors

    def check_min_leq_max(self, objects: list[GraphQLObjectType], directive: str) -> list[str]:
        errors = []
        for obj in objects:
            for fname, field in obj.fields.items():
                if has_given_directive(field, directive):
                    args = get_directive_arguments(field, directive)
                    try:
                        min_val = args.get("min")
                        max_val = args.get("max")
                        if min_val is not None and max_val is not None and float(min_val) > float(max_val):
                            errors.append(f"[{directive}] {obj.name}.{fname} has min > max ({min_val} > {max_val})")
                    except (ValueError, TypeError) as e:
                        errors.append(f"[{directive}] {obj.name}.{fname} has invalid min/max values: {e}")

        return errors

    def run(self, objects: list[GraphQLObjectType]) -> list[str]:
        errors: list[str] = []
        # instanceTag field rule
        for obj in objects:
            if "instanceTag" in obj.fields:
                field = obj.fields["instanceTag"]
                output_type = self.schema.get_type(get_named_type(field.type).name)
                if not (isinstance(output_type, GraphQLObjectType) and has_given_directive(output_type, "instanceTag")):
                    errors.append(
                        f"[instanceTag] {obj.name}.instanceTag must reference an object type with @instanceTag"
                    )

        # instanceTag object fields must be enums
        for obj in objects:
            if has_given_directive(obj, "instanceTag"):
                for fname, field in obj.fields.items():
                    if not isinstance(field.type, GraphQLEnumType):
                        errors.append(f"[instanceTag] {obj.name}.{fname} must be an enum (in @instanceTag object)")

        errors += self.check_min_leq_max(objects, "range")
        errors += self.check_min_leq_max(objects, "cardinality")
        errors += self.check_cardinality_on_list_only(objects)

        if self.naming_config:
            errors += check_naming_conventions(self.schema, self.naming_config)

        return errors
