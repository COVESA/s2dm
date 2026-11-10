from collections.abc import Sequence
from typing import Literal, TypeGuard

from graphql import DocumentNode, parse, print_ast
from graphql.language.ast import (
    DefinitionNode,
    DirectiveDefinitionNode,
    EnumTypeDefinitionNode,
    FieldDefinitionNode,
    Node,
    ObjectTypeDefinitionNode,
    ScalarTypeDefinitionNode,
)

from s2dm.utils.compose.models import (
    DirectiveDefinitionConflict,
    EnumDefinitionConflict,
    QueryFieldConflict,
    ScalarDefinitionConflict,
    SchemaDefinition,
)
from s2dm.utils.schema_definitions import (
    is_directive_definition_superset,
    is_enum_definition_superset,
    is_field_definition_superset,
    is_scalar_definition_superset,
)
from s2dm.utils.sequence import get_sequence_or_empty

DefinitionKind = Literal["directive", "scalar", "enum"]

QUERY_TYPE_NAME = "Query"


def _printed_node_set(nodes: Sequence[Node] | None) -> frozenset[str]:
    """Return the printed nodes as a set, so the same nodes in any order compare equal."""
    node_sequence = get_sequence_or_empty(nodes)
    printed_nodes = {print_ast(node) for node in node_sequence}
    return frozenset(printed_nodes)


class SharedDefinitionResolver:
    """Reconcile shared directive, scalar, and enum definitions, and Query fields, across schema sources.

    The resolver extracts directive/scalar/enum definitions out of every schema, reports incompatible
    redeclarations as conflicts, and emits the reconciled set as a single block. Identical redeclarations
    collapse to one; differing ones are a conflict, unless ``merge_shared_definitions`` lets a directive or
    scalar superset absorb the others. It also stitches every schema's ``Query`` type into a single merged
    type by unioning their fields; a field redeclared identically across schemas collapses to one, while a
    field name redeclared with a different signature is reported as a conflict. Each schema is left with
    its remaining type definitions only for downstream composition.
    """

    def __init__(self, schema_definitions: list[SchemaDefinition], merge_shared_definitions: bool = False) -> None:
        self.merge_shared_definitions = merge_shared_definitions
        self.superset_definitions_by_key: dict[tuple[DefinitionKind, str], DefinitionNode] = {}
        self.merged_query_definition: ObjectTypeDefinitionNode | None = None
        self.schema_documents = [
            (schema_definition.source_label, parse(schema_definition.content))
            for schema_definition in schema_definitions
        ]
        incompatible_definitions_items = self._incompatible_definitions().items()
        self.directive_conflicts = tuple(
            DirectiveDefinitionConflict(directive_name=name, schema_source_labels=schema_source_labels)
            for (kind, name), schema_source_labels in incompatible_definitions_items
            if kind == "directive"
        )
        self.scalar_conflicts = tuple(
            ScalarDefinitionConflict(scalar_name=name, schema_source_labels=schema_source_labels)
            for (kind, name), schema_source_labels in incompatible_definitions_items
            if kind == "scalar"
        )
        self.enum_conflicts = tuple(
            EnumDefinitionConflict(enum_name=name, schema_source_labels=schema_source_labels)
            for (kind, name), schema_source_labels in incompatible_definitions_items
            if kind == "enum"
        )
        self.root_type_conflicts = self._resolve_query_fields()

    def resolved_definitions_sdl(self) -> str:
        """Return the reconciled directives, scalars, and enums as a single SDL block, each declared once.

        Keeps the first declaration of every ``(kind, name)`` in dependency order. Identical
        redeclarations collapse to that copy; incompatible ones are reported via ``directive_conflicts`` /
        ``scalar_conflicts`` / ``enum_conflicts`` and must block the build before this is written.
        """
        seen_keys: set[tuple[DefinitionKind, str]] = set()
        shared_definitions: list[DefinitionNode] = []
        for _, document in self.schema_documents:
            for definition in document.definitions:
                shared_definition = self._as_shared_definition(definition)
                if shared_definition is None:
                    continue
                key, _ = shared_definition
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                superset_definition = self.superset_definitions_by_key.get(key)
                if superset_definition is not None:
                    shared_definitions.append(superset_definition)
                    continue
                shared_definitions.append(definition)
        if self.merged_query_definition is not None:
            shared_definitions.append(self.merged_query_definition)
        if not shared_definitions:
            return ""
        return print_ast(DocumentNode(definitions=tuple(shared_definitions)))

    def schema_definitions_without_shared_definitions(self) -> list[SchemaDefinition]:
        """Return each schema definition with its directive, scalar, enum, and Query declarations removed."""
        type_only_schema_definitions: list[SchemaDefinition] = []
        for source_label, document in self.schema_documents:
            type_definitions = tuple(
                definition
                for definition in document.definitions
                if self._as_shared_definition(definition) is None and not self._is_query_definition(definition)
            )
            type_only_schema_definitions.append(
                SchemaDefinition(
                    content=print_ast(DocumentNode(definitions=type_definitions)),
                    source_label=source_label,
                )
            )
        return type_only_schema_definitions

    def _resolve_query_fields(self) -> tuple[QueryFieldConflict, ...]:
        """Union every schema's ``Query`` fields into ``merged_query_definition``, reporting name clashes."""
        query_definitions: list[ObjectTypeDefinitionNode] = [
            definition
            for _, document in self.schema_documents
            for definition in document.definitions
            if self._is_query_definition(definition)
        ]
        if not query_definitions:
            return ()

        field_occurrences_by_name: dict[str, list[tuple[str, FieldDefinitionNode]]] = {}
        for source_label, document in self.schema_documents:
            for definition in document.definitions:
                if not self._is_query_definition(definition):
                    continue
                for field in get_sequence_or_empty(definition.fields):
                    field_occurrences_by_name.setdefault(field.name.value, []).append((source_label, field))

        conflicts: list[QueryFieldConflict] = []
        merged_fields_by_name: dict[str, FieldDefinitionNode] = {}
        for field_name, occurrences in field_occurrences_by_name.items():
            fields = [field for _, field in occurrences]
            merged_field = self._resolve_query_field(fields)
            if merged_field is None:
                conflicts.append(
                    QueryFieldConflict(
                        type_name=QUERY_TYPE_NAME,
                        field_name=field_name,
                        schema_source_labels=tuple(source_label for source_label, _ in occurrences),
                    )
                )
                merged_field = fields[0]
            merged_fields_by_name[field_name] = merged_field

        first_query_definition = query_definitions[0]
        self.merged_query_definition = ObjectTypeDefinitionNode(
            name=first_query_definition.name,
            interfaces=first_query_definition.interfaces,
            directives=first_query_definition.directives,
            fields=tuple(merged_fields_by_name.values()),
        )
        return tuple(conflicts)

    def _resolve_query_field(self, fields: list[FieldDefinitionNode]) -> FieldDefinitionNode | None:
        """Return the single field these occurrences collapse to, or ``None`` if they conflict.

        Identical redeclarations (compared order-insensitively) collapse to the first; differing ones
        conflict unless ``merge_shared_definitions`` lets a superset field absorb the others.
        """
        identities = {self._field_identity(field) for field in fields}
        if len(identities) == 1:
            return fields[0]
        if self.merge_shared_definitions:
            return self._select_superset_field(fields)
        return None

    def _select_superset_field(self, fields: list[FieldDefinitionNode]) -> FieldDefinitionNode | None:
        for candidate in fields:
            is_superset_of_all = all(is_field_definition_superset(candidate, field) for field in fields)
            if is_superset_of_all:
                return candidate
        return None

    @staticmethod
    def _is_query_definition(definition: Node) -> TypeGuard[ObjectTypeDefinitionNode]:
        return isinstance(definition, ObjectTypeDefinitionNode) and definition.name.value == QUERY_TYPE_NAME

    def conflict_messages(self) -> list[str]:
        """Return generic conflict messages for incompatible shared definitions."""
        messages: list[str] = []

        for directive_conflict in self.directive_conflicts:
            source_labels = ", ".join(directive_conflict.schema_source_labels)
            messages.append(
                f"Multiple definitions of directive `@{directive_conflict.directive_name}` found in [{source_labels}]"
            )

        for scalar_conflict in self.scalar_conflicts:
            source_labels = ", ".join(scalar_conflict.schema_source_labels)
            messages.append(
                f"Multiple definitions of scalar `{scalar_conflict.scalar_name}` found in [{source_labels}]"
            )

        for enum_conflict in self.enum_conflicts:
            source_labels = ", ".join(enum_conflict.schema_source_labels)
            messages.append(f"Multiple definitions of enum `{enum_conflict.enum_name}` found in [{source_labels}]")

        for root_type_conflict in self.root_type_conflicts:
            source_labels = ", ".join(root_type_conflict.schema_source_labels)
            messages.append(
                f"Multiple incompatible definitions of field "
                f"`{root_type_conflict.type_name}.{root_type_conflict.field_name}` found in [{source_labels}]"
            )

        return messages

    def _incompatible_definitions(self) -> dict[tuple[DefinitionKind, str], tuple[str, ...]]:
        source_labels_by_key: dict[tuple[DefinitionKind, str], list[str]] = {}
        identities_by_key: dict[tuple[DefinitionKind, str], set[tuple[object, ...]]] = {}
        definitions_by_key: dict[tuple[DefinitionKind, str], list[DefinitionNode]] = {}
        for source_label, document in self.schema_documents:
            for definition in document.definitions:
                shared_definition = self._as_shared_definition(definition)
                if shared_definition is None:
                    continue
                key, identity = shared_definition
                source_labels_by_key.setdefault(key, []).append(source_label)
                identities_by_key.setdefault(key, set()).add(identity)
                definitions_by_key.setdefault(key, []).append(definition)

        incompatible_definitions: dict[tuple[DefinitionKind, str], tuple[str, ...]] = {}
        for key, schema_source_labels in source_labels_by_key.items():
            has_multiple_sources = len(schema_source_labels) > 1
            has_different_identities = len(identities_by_key[key]) > 1
            if not has_multiple_sources or not has_different_identities:
                continue

            if self.merge_shared_definitions:
                definitions = definitions_by_key[key]
                superset_definition = self._select_superset_definition(key, definitions)
                if superset_definition is not None:
                    self.superset_definitions_by_key[key] = superset_definition
                    continue

            incompatible_definitions[key] = tuple(schema_source_labels)

        return incompatible_definitions

    def _select_superset_definition(
        self, key: tuple[DefinitionKind, str], definitions: list[DefinitionNode]
    ) -> DefinitionNode | None:
        kind, _ = key
        for candidate in definitions:
            candidate_is_superset = True
            for definition in definitions:
                if kind == "directive":
                    is_superset = (
                        isinstance(candidate, DirectiveDefinitionNode)
                        and isinstance(definition, DirectiveDefinitionNode)
                        and is_directive_definition_superset(candidate, definition)
                    )
                elif kind == "scalar":
                    is_superset = (
                        isinstance(candidate, ScalarTypeDefinitionNode)
                        and isinstance(definition, ScalarTypeDefinitionNode)
                        and is_scalar_definition_superset(candidate, definition)
                    )
                elif kind == "enum":
                    is_superset = (
                        isinstance(candidate, EnumTypeDefinitionNode)
                        and isinstance(definition, EnumTypeDefinitionNode)
                        and is_enum_definition_superset(candidate, definition)
                    )
                else:
                    return None
                if not is_superset:
                    candidate_is_superset = False
                    break
            if candidate_is_superset:
                return candidate
        return None

    @staticmethod
    def _as_shared_definition(definition: Node) -> tuple[tuple[DefinitionKind, str], tuple[object, ...]] | None:
        """Map a directive/scalar/enum definition to its ``((kind, name), identity)``; ``None`` otherwise.

        Two schemas declaring the same ``(kind, name)`` must declare it identically: equal identity
        means the declarations are interchangeable and collapse to one; differing identity is a conflict.
        """
        if isinstance(definition, DirectiveDefinitionNode):
            return ("directive", definition.name.value), SharedDefinitionResolver._directive_identity(definition)
        if isinstance(definition, ScalarTypeDefinitionNode):
            return ("scalar", definition.name.value), SharedDefinitionResolver._scalar_identity(definition)
        if isinstance(definition, EnumTypeDefinitionNode):
            return ("enum", definition.name.value), SharedDefinitionResolver._enum_identity(definition)
        return None

    @staticmethod
    def _directive_identity(node: DirectiveDefinitionNode) -> tuple[object, ...]:
        """Directive identity: its locations and argument definitions, compared order-insensitively."""
        locations = _printed_node_set(node.locations)
        arguments = _printed_node_set(node.arguments)
        return (locations, arguments, node.repeatable)

    @staticmethod
    def _scalar_identity(node: ScalarTypeDefinitionNode) -> tuple[object, ...]:
        """Scalar identity: the directives applied to it, compared order-insensitively."""
        directives = _printed_node_set(node.directives)
        return (directives,)

    @staticmethod
    def _enum_identity(node: EnumTypeDefinitionNode) -> tuple[object, ...]:
        """Enum identity: its directives and each value's name and directives, compared order-insensitively."""
        directives = _printed_node_set(node.directives)
        value_identities: set[tuple[str, frozenset[str]]] = set()
        for value in get_sequence_or_empty(node.values):
            value_directives = _printed_node_set(value.directives)
            value_identities.add((value.name.value, value_directives))
        values = frozenset(value_identities)
        return (directives, values)

    @staticmethod
    def _field_identity(node: FieldDefinitionNode) -> tuple[object, ...]:
        """Field identity: its return type, arguments, and directives, compared order-insensitively."""
        return_type = print_ast(node.type)
        arguments = _printed_node_set(node.arguments)
        directives = _printed_node_set(node.directives)
        return (return_type, arguments, directives)
