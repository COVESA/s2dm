from graphql import GraphQLEnumType, GraphQLObjectType, GraphQLSchema, get_named_type

from s2dm.exporters.utils.directive import get_directive_arguments, has_given_directive


class ConstraintChecker:
    def __init__(self, schema: GraphQLSchema):
        self.schema = schema

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

        # generic min/max checks
        errors += self.check_min_leq_max(objects, "range")
        errors += self.check_min_leq_max(objects, "cardinality")

        # ToDo: NAMING: (Placeholder for naming convention checks)
        # Example: Enforce PascalCase for type names, camelCase for field names
        # for obj in objects:
        #     if not obj.name[0].isupper():
        #         errors.append(f"[naming] Type {obj.name} should be PascalCase")
        #     for fname in obj.fields:
        #         if not fname[0].islower():
        #             errors.append(f"[naming] Field {obj.name}.{fname} should be camelCase")

        return errors
