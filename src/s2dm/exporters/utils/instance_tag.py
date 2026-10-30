from copy import copy
from itertools import product
from typing import Any, NamedTuple, cast

from graphql import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLSchema,
    get_named_type,
    get_nullable_type,
    is_list_type,
    is_non_null_type,
)
from graphql.language.ast import (
    ConstArgumentNode,
    ConstDirectiveNode,
    ConstListValueNode,
    FieldDefinitionNode,
    NameNode,
    StringValueNode,
)
from pydantic import BaseModel, Field

from s2dm import log
from s2dm.constants.directive import Directive, DirectiveArgument
from s2dm.exporters.utils.annotated_schema import FieldMetadata, TypeMetadata
from s2dm.exporters.utils.directive import (
    get_argument_content,
    has_given_directive,
)
from s2dm.exporters.utils.extraction import get_all_object_types
from s2dm.exporters.utils.naming import convert_name
from s2dm.exporters.utils.naming_config import (
    CaseFormat,
    ContextType,
    ElementType,
    NamingConventionConfig,
    get_case_for_element,
)

InstanceTagSource = GraphQLObjectType | GraphQLEnumType


class _ExpandableField(NamedTuple):
    """Everything discovered for one expandable field, captured before any schema mutation."""

    parent_type: GraphQLObjectType
    field_name: str
    base_type: GraphQLObjectType
    tag_field_name: str
    source_type_name: str
    instance_tag_dict: dict[str, list[str]]
    leaf_nullable: bool
    original_field: GraphQLField
    exclude: list[str]


class _ResolvedInstanceTag(NamedTuple):
    """The valid @instanceTag field of an object type, resolved in a single pass."""

    field_name: str
    source_type: InstanceTagSource


def join_instance(instance: tuple[str, ...]) -> str:
    """
    Join the dimension values of an instance into a dotted name, such as `A.B`.

    Args:
        instance: The instance, as a tuple of dimension values.

    Returns:
        str: The dotted name.
    """
    return ".".join(instance)


def get_field_coordinate(type_name: str, field_name: str) -> str:
    """
    Join a type name and a field name into a coordinate, such as `Type.field`.

    Args:
        type_name: The type that declares the field.
        field_name: The field.

    Returns:
        str: The coordinate.
    """
    return f"{type_name}.{field_name}"


def is_instance_tag_field(field: GraphQLField) -> bool:
    return has_given_directive(field, Directive.INSTANCE_TAG)


def get_instance_tag_type(field: GraphQLField, schema: GraphQLSchema) -> InstanceTagSource | None:
    if not is_instance_tag_field(field):
        return None

    named_type = get_named_type(field.type)
    output_type = schema.get_type(named_type.name)
    if not isinstance(output_type, GraphQLObjectType | GraphQLEnumType):
        return None

    if not has_given_directive(output_type, Directive.INSTANCE_TAG):
        return None

    return output_type


def is_valid_instance_tag_field(field: GraphQLField, schema: GraphQLSchema) -> bool:
    """
    Check if the given field is a valid instanceTag field.
    A valid instanceTag field is annotated with @instanceTag and references an
    object type with the @instanceTag directive.

    Args:
        field (GraphQLField): The field to check.
        schema (GraphQLSchema): The GraphQL schema to validate against.

    Returns:
        bool: True if the field's output type is a valid instanceTag, False otherwise.
    """
    return get_instance_tag_type(field, schema) is not None


def resolve_instance_tag(object_type: GraphQLObjectType, schema: GraphQLSchema) -> _ResolvedInstanceTag | None:
    """
    Resolve the single valid @instanceTag field of an object type.

    This is the shared lookup behind the public instanceTag helpers: it locates the valid
    instanceTag field (if any) and the type it references, so callers stop re-walking the fields.

    Args:
        object_type (GraphQLObjectType): The object type to inspect.
        schema (GraphQLSchema): The GraphQL schema to validate against.

    Returns:
        _ResolvedInstanceTag | None: The resolved instanceTag, or None if the object has none.
    """
    for field_name, field in object_type.fields.items():
        source_type = get_instance_tag_type(field, schema)
        if source_type is not None:
            return _ResolvedInstanceTag(field_name, source_type)
    return None


def _tag_dimensions_from_source(tag_field_name: str, source_type: InstanceTagSource) -> dict[str, list[str]]:
    """
    Return the instanceTag dimensions of a source type as an ordered mapping.

    Both object- and enum-backed sources are normalized to one ordered mapping of dimension name to
    its enum values, so type construction and name expansion share a single representation.

    Args:
        tag_field_name (str): The name of the field that references the source type.
        source_type (InstanceTagSource): The resolved instanceTag source type.

    Returns:
        dict[str, list[str]]: Ordered mapping of dimension name to enum values.
    """
    if isinstance(source_type, GraphQLObjectType):
        return get_instance_tag_dict(source_type)
    return {tag_field_name: list(source_type.values.keys())}


def get_instance_tag_dict(
    instance_tag_object: GraphQLObjectType,
) -> dict[str, list[str]]:
    """
    Given a valid instance tag object type, return the list of all enum values by level.

    Args:
        instance_tag_object (GraphQLObjectType): The instance tag object type to process.

    Returns:
        dict[str, list[str]]: A dictionary where keys are field names and values are lists of enum values.
    """
    instance_tag_dict = {}

    for field_name, field in instance_tag_object.fields.items():
        field_type = field.type
        if is_non_null_type(field_type):
            field_type = cast(GraphQLNonNull[Any], field_type).of_type

        if isinstance(field_type, GraphQLEnumType):
            instance_tag_dict[field_name] = list(field_type.values.keys())
        else:
            raise TypeError(f"Field '{field_name}' in object '{instance_tag_object.name}' is not an enum.")

    return instance_tag_dict


def get_instance_tag_case(naming_config: NamingConventionConfig | None) -> CaseFormat | None:
    """Return the configured case for instanceTag values, or None when unconfigured."""
    if naming_config is None:
        return None
    return get_case_for_element(ElementType.INSTANCE_TAG, None, naming_config)


def _read_exclude_entries(tag_field: GraphQLField, source_type: InstanceTagSource) -> tuple[list[str], list[str]]:
    """
    Read the `exclude` lists of the @instanceTag on a tag field and on its source type.

    Args:
        tag_field: The tag field.
        source_type: The source type of the tag field.

    Returns:
        tuple[list[str], list[str]]: The dotted entries on the field, and the dotted entries on the source type.
    """
    field_exclude = get_argument_content(tag_field, Directive.INSTANCE_TAG, DirectiveArgument.EXCLUDE) or []
    source_exclude = get_argument_content(source_type, Directive.INSTANCE_TAG, DirectiveArgument.EXCLUDE) or []
    return field_exclude, source_exclude


def collect_expandable_fields(schema: GraphQLSchema) -> list[_ExpandableField]:
    """Find every list field whose item type carries a valid instanceTag, without touching the schema."""
    expandable_fields = []
    for parent_type in get_all_object_types(schema):
        for field_name, field in parent_type.fields.items():
            base_type = get_named_type(field.type)
            if not isinstance(base_type, GraphQLObjectType):
                continue
            resolved = resolve_instance_tag(base_type, schema)
            if resolved is None:
                continue

            unwrapped = get_nullable_type(field.type)
            if not is_list_type(unwrapped):
                continue
            item_type = unwrapped.of_type

            tag_field = base_type.fields[resolved.field_name]
            field_exclude, source_exclude = _read_exclude_entries(tag_field, resolved.source_type)
            exclude = list(dict.fromkeys([*field_exclude, *source_exclude]))

            expandable_fields.append(
                _ExpandableField(
                    parent_type=parent_type,
                    field_name=field_name,
                    base_type=base_type,
                    tag_field_name=resolved.field_name,
                    source_type_name=resolved.source_type.name,
                    instance_tag_dict=_tag_dimensions_from_source(resolved.field_name, resolved.source_type),
                    leaf_nullable=not is_non_null_type(item_type),
                    original_field=field,
                    exclude=exclude,
                )
            )
    return expandable_fields


def included_instances(
    expandable: _ExpandableField,
    instance_tag_case: CaseFormat | None,
) -> list[tuple[str, ...]]:
    """
    Return the instances the field expands into after applying its exclude list.

    Exclude entries are authored against the schema's literal enum values; when a naming
    convention has renamed those values, each dotted segment is cased the same way before
    matching. An entry that matches no instance is a configuration error.

    Args:
        expandable: The field being expanded, carrying its dimensions and exclude list.
        instance_tag_case: The case applied to instanceTag values, or None when unconfigured.

    Returns:
        list[tuple[str, ...]]: The included instances in cartesian-product order.

    Raises:
        ValueError: If any exclude entry matches no instance.
    """
    instances = list(product(*expandable.instance_tag_dict.values()))
    if not expandable.exclude:
        return instances

    included, unmatched = _instances_not_named(instances, expandable.exclude, instance_tag_case)
    if unmatched:
        field_coordinate = get_field_coordinate(expandable.parent_type.name, expandable.field_name)
        supported_names = sorted(join_instance(instance) for instance in instances)
        raise ValueError(
            f"@instanceTag exclude entries {sorted(unmatched)} on "
            f"'{field_coordinate}' match no instance; "
            f"supported instances are {supported_names}"
        )

    return included


def _instances_not_named(
    instances: list[tuple[str, ...]],
    entries: list[str],
    instance_tag_case: CaseFormat | None,
) -> tuple[list[tuple[str, ...]], list[str]]:
    """
    Return the instances that no dotted entry names.

    Entries use the enum values as written in the schema. If a naming convention renamed the values,
    each part of an entry is renamed the same way before matching.

    Args:
        instances: The instances, as tuples of dimension values.
        entries: Dotted entries, such as `A.B`.
        instance_tag_case: The case of instanceTag values, or None if not configured.

    Returns:
        tuple[list[tuple[str, ...]], list[str]]: The instances that no entry names, in the same order,
        and the entries that name no instance.
    """

    def normalize(entry: str) -> tuple[str, ...]:
        segments = entry.split(".")
        if instance_tag_case:
            segments = [convert_name(segment, instance_tag_case) for segment in segments]
        return tuple(segments)

    unmatched = {normalize(entry): entry for entry in entries}
    remaining: list[tuple[str, ...]] = []
    for instance in instances:
        if unmatched.pop(instance, None) is None:
            remaining.append(instance)

    unmatched_values = unmatched.values()
    unmatched_entries = list(unmatched_values)
    return remaining, unmatched_entries


class _DefinedInstances(NamedTuple):
    """A tag field and the instances it defines before a query narrows them."""

    tag_field: GraphQLField
    dimensions: dict[str, list[str]]
    field_exclude: list[str]
    instances: list[tuple[str, ...]]

    @property
    def names(self) -> list[str]:
        """The defined instances as dotted names, such as `A.B`, in the order of the dimension product."""
        return [join_instance(instance) for instance in self.instances]


def _read_defined_instances(schema: GraphQLSchema, object_type_name: str, tag_field_name: str) -> _DefinedInstances:
    """
    Find a tag field and the instances it defines after its own `exclude` lists.

    Entries that name no instance are ignored here. Expansion reports them.

    Args:
        schema: The schema.
        object_type_name: The type that declares the tag field.
        tag_field_name: The tag field.

    Returns:
        _DefinedInstances: The field, its dimensions, the `exclude` list on the field, and the defined instances.
    """
    named_type = schema.get_type(object_type_name)
    object_type = cast(GraphQLObjectType, named_type)
    tag_field = object_type.fields[tag_field_name]
    tag_type = get_instance_tag_type(tag_field, schema)
    source_type = cast(InstanceTagSource, tag_type)
    dimensions = _tag_dimensions_from_source(tag_field_name, source_type)
    field_exclude, source_exclude = _read_exclude_entries(tag_field, source_type)
    dimension_values = dimensions.values()
    combinations = product(*dimension_values)
    all_instances = list(combinations)
    defined_instances, _ = _instances_not_named(all_instances, [*field_exclude, *source_exclude], None)
    return _DefinedInstances(tag_field, dimensions, field_exclude, defined_instances)


def _exclude_instances(defined_instances: _DefinedInstances, newly_excluded: list[tuple[str, ...]]) -> None:
    """
    Add instances to the `exclude` list of the tag field's @instanceTag.

    The schema is printed from the AST nodes. So this replaces the field's AST node with a copy that
    has the longer `exclude` list. This changes the field in place.

    Args:
        defined_instances: The tag field and its current `exclude` list.
        newly_excluded: The instances to add.
    """
    if not newly_excluded:
        return

    newly_excluded_names = [join_instance(instance) for instance in newly_excluded]
    exclude_entries = [*defined_instances.field_exclude, *newly_excluded_names]
    exclude_values = tuple(StringValueNode(value=entry) for entry in exclude_entries)
    exclude_name = NameNode(value=DirectiveArgument.EXCLUDE.value)
    exclude_list = ConstListValueNode(values=exclude_values)
    exclude_argument = ConstArgumentNode(name=exclude_name, value=exclude_list)

    field_node = cast(FieldDefinitionNode, defined_instances.tag_field.ast_node)
    directives: list[ConstDirectiveNode] = []
    for directive in field_node.directives:
        if directive.name.value != Directive.INSTANCE_TAG.value:
            directives.append(directive)
            continue
        other_arguments = [
            argument for argument in directive.arguments if argument.name.value != DirectiveArgument.EXCLUDE.value
        ]
        narrowed_directive = copy(directive)
        narrowed_directive.arguments = (*other_arguments, exclude_argument)
        directives.append(narrowed_directive)

    narrowed_field_node = copy(field_node)
    narrowed_field_node.directives = tuple(directives)
    defined_instances.tag_field.ast_node = narrowed_field_node


def get_defined_instance_names(schema: GraphQLSchema, object_type_name: str, tag_field_name: str) -> list[str]:
    """
    Return the instances that a tag field defines, as dotted names such as `A.B`.

    Args:
        schema: The schema.
        object_type_name: The type that declares the tag field.
        tag_field_name: The tag field.

    Returns:
        list[str]: The defined instances, in the order of the dimension product.
    """
    defined_instances = _read_defined_instances(schema, object_type_name, tag_field_name)
    return defined_instances.names


class InstanceTagFieldInfo(BaseModel):
    """The dimensions and instances that @pick can name on an instance tag field."""

    dimensions: dict[str, list[str]] = Field(description="The enum values of each dimension, in schema order")
    instances: list[str] = Field(
        description="The defined instances as dotted names, without the entries of the exclude lists"
    )


def get_instance_tag_fields(schema: GraphQLSchema) -> dict[str, InstanceTagFieldInfo]:
    """
    Index every instance tag field of the schema by `Type.field`, with its dimensions and defined instances.

    The defined instances are the ones that @pick can name: the product of the dimensions, without
    the entries in the `exclude` lists of the field and of the tag type.

    Args:
        schema: The schema.

    Returns:
        dict[str, InstanceTagFieldInfo]: The instance tag fields by `Type.field`, in schema order.
    """
    tag_fields: dict[str, InstanceTagFieldInfo] = {}
    object_types = get_all_object_types(schema)
    for object_type in object_types:
        for field_name, field in object_type.fields.items():
            if not is_valid_instance_tag_field(field, schema):
                continue

            defined_instances = _read_defined_instances(schema, object_type.name, field_name)
            coordinate = get_field_coordinate(object_type.name, field_name)
            tag_fields[coordinate] = InstanceTagFieldInfo(
                dimensions=defined_instances.dimensions, instances=defined_instances.names
            )

    return tag_fields


def pick_instances(schema: GraphQLSchema, object_type_name: str, tag_field_name: str, entries: list[str]) -> None:
    """
    Keep only the named instances of a tag field, by excluding the other defined instances.

    Entries that name no defined instance are ignored here; `extract_and_validate_picks` reports them.
    This changes the field in place.

    Args:
        schema: The schema.
        object_type_name: The type that declares the tag field.
        tag_field_name: The tag field.
        entries: Dotted entries for the instances to keep, such as `A.B`.
    """
    defined_instances = _read_defined_instances(schema, object_type_name, tag_field_name)
    newly_excluded, _ = _instances_not_named(defined_instances.instances, entries, None)
    _exclude_instances(defined_instances, newly_excluded)


def _picked_combinations(
    defined_instances: _DefinedInstances, values_by_dimension: dict[str, list[str]]
) -> set[tuple[str, ...]]:
    """
    Return every combination of the picked dimension values.

    A dimension with no picked values keeps all its values.

    Args:
        defined_instances: The tag field and its dimensions.
        values_by_dimension: The values to keep, for each picked dimension.

    Returns:
        set[tuple[str, ...]]: The combinations, as tuples of dimension values.
    """
    picked_values = [
        values_by_dimension.get(dimension, values) for dimension, values in defined_instances.dimensions.items()
    ]
    combinations = product(*picked_values)
    return set(combinations)


def get_kept_instance_names(
    schema: GraphQLSchema, object_type_name: str, tag_field_name: str, values_by_dimension: dict[str, list[str]]
) -> list[str]:
    """
    Return the defined instances that the picked dimension values keep, as dotted names such as `A.B`.

    A dimension with no picked values keeps all its values.

    Args:
        schema: The schema.
        object_type_name: The type that declares the tag field.
        tag_field_name: The tag field.
        values_by_dimension: The values to keep, for each picked dimension.

    Returns:
        list[str]: The kept instances, in the order of the dimension product.
    """
    defined_instances = _read_defined_instances(schema, object_type_name, tag_field_name)
    picked_combinations = _picked_combinations(defined_instances, values_by_dimension)
    return [join_instance(instance) for instance in defined_instances.instances if instance in picked_combinations]


def _build_instance_types(
    base_type: GraphQLObjectType,
    dimensions: list[str],
    instances: list[tuple[str, ...]],
    leaf_nullable: bool,
) -> tuple[GraphQLObjectType, list[GraphQLObjectType]]:
    """
    Build the intermediate type tree spanning the given instances.

    The instances form a trie keyed by dimension: sibling branches with an identical set of
    remaining instances share one type, while branches left asymmetric by an exclusion split
    into their own types named after the path that reaches them.

    Example:
        dimensions=["a", "b"] over A1/A2 x B1/B2, with leaves pointing at the base type Base.

        Nothing excluded - both A branches expand identically, so the b level is built once and shared:
            Base_A -> { A1: Base_B, A2: Base_B }
            Base_B -> { B1: Base, B2: Base }

        Excluding A1.B1 - the A branches now differ, so each gets its own b type:
            Base_A    -> { A1: Base_A1_B, A2: Base_A2_B }
            Base_A1_B -> { B2: Base }
            Base_A2_B -> { B1: Base, B2: Base }

    Args:
        base_type: The base type the leaves point at (e.g., Base).
        dimensions: The instanceTag dimension names, outermost first.
        instances: The included instances, each aligned with ``dimensions``.
        leaf_nullable: Whether the field's leaf type (list item, or the base type for a non-list field) was nullable.

    Returns:
        tuple: The top intermediate type and every type created while building the tree.
    """
    created: list[GraphQLObjectType] = []

    def build(level: int, remaining: list[tuple[str, ...]], name_prefix: str) -> GraphQLObjectType:
        dimension = dimensions[level]
        groups: dict[str, list[tuple[str, ...]]] = {}
        for suffix in remaining:
            groups.setdefault(suffix[0], []).append(suffix[1:])

        fields: dict[str, GraphQLField] = {}
        if level == len(dimensions) - 1:
            leaf_type = base_type if leaf_nullable else GraphQLNonNull(base_type)
            fields = {value: GraphQLField(leaf_type) for value in groups}
        else:
            siblings_share_subtree = len({frozenset(subsuffixes) for subsuffixes in groups.values()}) == 1
            if siblings_share_subtree:
                shared = build(level + 1, next(iter(groups.values())), name_prefix)
                fields = {value: GraphQLField(GraphQLNonNull(shared)) for value in groups}
            else:
                for value, subsuffixes in groups.items():
                    child = build(level + 1, subsuffixes, f"{name_prefix}{value}_")
                    fields[value] = GraphQLField(GraphQLNonNull(child))

        instance_type = GraphQLObjectType(name=f"{base_type.name}_{name_prefix}{dimension.capitalize()}", fields=fields)
        created.append(instance_type)
        log.debug(f"Created intermediate type '{instance_type.name}' with fields: {list(fields)}")
        return instance_type

    top_type = build(0, instances, "")
    return top_type, created


def _apply_expansion(
    expandable: _ExpandableField,
    top_type: GraphQLObjectType,
    intermediate_types: list[GraphQLObjectType],
    instances: list[tuple[str, ...]],
    type_case: CaseFormat | None,
    field_case: CaseFormat | None,
    new_types: dict[str, GraphQLObjectType],
    field_metadata: dict[tuple[str, str], FieldMetadata],
) -> None:
    """Apply naming to the built types and replace the parent field with its expanded form."""
    for intermediate_type in intermediate_types:
        if type_case:
            intermediate_type.name = convert_name(intermediate_type.name, type_case)
        new_types[intermediate_type.name] = intermediate_type

    new_field_name = convert_name(expandable.base_type.name, field_case) if field_case else expandable.base_type.name

    field_metadata[(expandable.parent_type.name, new_field_name)] = FieldMetadata(
        resolved_names=[f"{new_field_name}.{join_instance(instance)}" for instance in instances],
        resolved_type=expandable.base_type.name,
        is_expanded=True,
        original_field=expandable.original_field,
        instances=list(expandable.instance_tag_dict.values()),
    )

    new_field = GraphQLField(type_=GraphQLNonNull(top_type), description=expandable.original_field.description)
    del expandable.parent_type.fields[expandable.field_name]
    expandable.parent_type.fields[new_field_name] = new_field
    log.debug(
        f"Replaced field '{expandable.field_name}' with '{new_field_name}' in type '{expandable.parent_type.name}'"
    )


def _cleanup_instance_tag_artifacts(schema: GraphQLSchema, expandable_fields: list[_ExpandableField]) -> None:
    """Remove the instanceTag source types and the now-redundant instanceTag fields on base types.

    Scoped to expandable_fields so a source type still referenced by an un-expanded field survives.
    """
    types_to_remove = {expandable.source_type_name for expandable in expandable_fields}

    for base_type, tag_field_name in {
        expandable.base_type: expandable.tag_field_name for expandable in expandable_fields
    }.items():
        if tag_field_name in base_type.fields:
            del base_type.fields[tag_field_name]
            log.debug(f"Removed '{tag_field_name}' instanceTag field from type '{base_type.name}'")

    for type_name in types_to_remove:
        if type_name in schema.type_map:
            del schema.type_map[type_name]
            log.debug(f"Removed type '{type_name}' with @instanceTag directive from schema")


def expand_instances_in_schema(
    schema: GraphQLSchema,
    naming_config: NamingConventionConfig | None = None,
) -> tuple[GraphQLSchema, dict[str, "TypeMetadata"], dict[tuple[str, str], "FieldMetadata"]]:
    """
    Expand instance-tagged fields in a GraphQL schema into nested object structures.

    For fields with types that contain instanceTag fields, this function creates intermediate
    GraphQL types representing each level of the instance tag hierarchy and modifies the
    parent field to use the singular type name.

    Args:
        schema: The GraphQL schema to modify
        naming_config: Optional naming configuration for transforming type and field names

    Returns:
        Tuple of (modified schema, type metadata dict, field metadata dict)
    """
    log.info("Starting instance expansion in schema")

    expandable_fields = collect_expandable_fields(schema)
    log.info(f"Found {len(expandable_fields)} expandable fields")

    def case_for(element: ElementType, context: ContextType | None) -> CaseFormat | None:
        return get_case_for_element(element, context, naming_config) if naming_config else None

    type_case = case_for(ElementType.TYPE, ContextType.OBJECT)
    field_case = case_for(ElementType.FIELD, ContextType.OBJECT)
    instance_tag_case = get_instance_tag_case(naming_config)

    # TODO: Optimization - Cache the built type tree to avoid rebuilding it for every referencing field.
    # When multiple fields reference the same base type (e.g., Cabin.doors and Vehicle.doors both reference
    # [Door]), we build the Door_* intermediate types once per field. The instances are base-type determined
    # (the exclude list lives on the base type's instanceTag field), so the trees are identical and the
    # later-built one currently just overwrites the earlier in new_types.
    # A cache cannot key on base_type.name alone: leaf_nullable is per-field (e.g. [Door] vs [Door!]), so two
    # fields can need different leaf types under the same intermediate names. Key on (base_type.name,
    # leaf_nullable) and disambiguate the generated names accordingly before reusing the built tree.
    new_types: dict[str, GraphQLObjectType] = {}
    field_metadata: dict[tuple[str, str], FieldMetadata] = {}
    for expandable in expandable_fields:
        instances = included_instances(expandable, instance_tag_case)
        top_type, intermediate_types = _build_instance_types(
            expandable.base_type, list(expandable.instance_tag_dict), instances, expandable.leaf_nullable
        )
        _apply_expansion(
            expandable, top_type, intermediate_types, instances, type_case, field_case, new_types, field_metadata
        )

    _cleanup_instance_tag_artifacts(schema, expandable_fields)
    schema.type_map.update(new_types)

    type_metadata = {name: TypeMetadata(source=None, is_intermediate_type=True) for name in new_types}
    log.info(f"Instance expansion complete. Created {len(new_types)} intermediate types")

    return schema, type_metadata, field_metadata
