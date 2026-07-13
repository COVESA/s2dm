from pathlib import Path
from typing import cast

from graphql import DocumentNode, parse, print_ast
from graphql.language.ast import (
    EnumTypeDefinitionNode,
    EnumTypeExtensionNode,
    InputObjectTypeDefinitionNode,
    InputObjectTypeExtensionNode,
    InterfaceTypeDefinitionNode,
    InterfaceTypeExtensionNode,
    NamedTypeNode,
    NameNode,
    Node,
    ObjectTypeDefinitionNode,
    ObjectTypeExtensionNode,
    ScalarTypeDefinitionNode,
    ScalarTypeExtensionNode,
    TypeDefinitionNode,
    TypeExtensionNode,
    UnionTypeDefinitionNode,
    UnionTypeExtensionNode,
)
from graphql.language.visitor import Visitor, visit

from s2dm.deps.compose.models import (
    DependencySchemaDocument,
    DependencySchemaInput,
    DependencyTypeNameConflict,
)
from s2dm.deps.models import DependencyMetadata
from s2dm.deps.naming import sanitize_prefix
from s2dm.utils.file import temp_files_from_contents

TYPE_DEFINITION_NODE_TYPES = (
    ObjectTypeDefinitionNode,
    InterfaceTypeDefinitionNode,
    InputObjectTypeDefinitionNode,
    EnumTypeDefinitionNode,
    ScalarTypeDefinitionNode,
    UnionTypeDefinitionNode,
)
_TYPE_EXTENSION_NODE_TYPES = (
    ObjectTypeExtensionNode,
    InterfaceTypeExtensionNode,
    InputObjectTypeExtensionNode,
    EnumTypeExtensionNode,
    ScalarTypeExtensionNode,
    UnionTypeExtensionNode,
)
_TYPE_NAMED_NODE_TYPES = TYPE_DEFINITION_NODE_TYPES + _TYPE_EXTENSION_NODE_TYPES


class DependencyTypePrefixVisitor(Visitor):
    """Rename selected GraphQL type definitions and references."""

    def __init__(self, rename_by_type_name: dict[str, str]) -> None:
        super().__init__()
        self.rename_by_type_name = rename_by_type_name

    def enter(
        self,
        node: Node,
        _key: str | int | None,
        _parent: object | None,
        _path: list[str | int],
        _ancestors: list[object],
    ) -> TypeDefinitionNode | TypeExtensionNode | NamedTypeNode | None:
        if isinstance(node, _TYPE_NAMED_NODE_TYPES):
            return self._rename_type_named_node(node)
        if isinstance(node, NamedTypeNode):
            return self._rename_named_type_reference(node)
        return None

    def _rename_named_type_reference(self, node: NamedTypeNode) -> NamedTypeNode | None:
        new_name = self.rename_by_type_name.get(node.name.value)
        if new_name is None:
            return None
        return NamedTypeNode(name=NameNode(value=new_name, loc=node.name.loc), loc=node.loc)

    def _rename_type_named_node(
        self, node: TypeDefinitionNode | TypeExtensionNode
    ) -> TypeDefinitionNode | TypeExtensionNode | None:
        new_name = self.rename_by_type_name.get(node.name.value)
        if new_name is None:
            return None

        node_values = {node_key: getattr(node, node_key) for node_key in node.keys}
        node_values["name"] = NameNode(value=new_name, loc=node.name.loc)
        return type(node)(**node_values)


class DependencySchemaBuilder:
    """Build dependency schemas from parsed documents with conflict-aware type renaming."""

    def __init__(self, dependency_schema_contents: list[DependencySchemaInput]) -> None:
        self.schema_documents = [
            self._parse_dependency_schema_document(dependency_schema_content)
            for dependency_schema_content in dependency_schema_contents
        ]

    def find_conflicts(self) -> tuple[DependencyTypeNameConflict, ...]:
        """Find GraphQL type names defined by more than one dependency."""
        dependencies_type_name_metadata: dict[str, list[DependencyMetadata]] = {}

        for schema_document in self.schema_documents:
            for type_name in schema_document.defined_type_names:
                dependencies_type_name_metadata.setdefault(type_name, []).append(schema_document.metadata)

        return tuple(
            DependencyTypeNameConflict(
                type_name=type_name,
                dependencies_metadata=tuple(dependencies_metadata),
            )
            for type_name, dependencies_metadata in dependencies_type_name_metadata.items()
            if len(dependencies_metadata) > 1
        )

    def write_auto_prefixed_schema_files(self) -> list[Path]:
        """Write dependency schemas after prefixing conflicting type definitions and references."""
        conflicting_type_names = {conflict.type_name for conflict in self.find_conflicts()}
        transformed_documents = [
            self._prefix_conflicting_type_names(schema_document, conflicting_type_names)
            for schema_document in self.schema_documents
        ]
        duplicate_type_names = self._find_duplicate_defined_type_names(transformed_documents)
        if duplicate_type_names:
            duplicate_type_names_message = ", ".join(sorted(duplicate_type_names))
            raise ValueError(f"Auto-prefix produced duplicate type definitions: {duplicate_type_names_message}")

        return temp_files_from_contents(
            print_ast(schema_document.document) for schema_document in transformed_documents
        )

    def _parse_dependency_schema_document(
        self, dependency_schema_content: DependencySchemaInput
    ) -> DependencySchemaDocument:
        document = parse(dependency_schema_content.schema_content)
        defined_type_names = frozenset(self._collect_defined_type_names(document))
        return DependencySchemaDocument(
            metadata=dependency_schema_content.metadata,
            document=document,
            defined_type_names=defined_type_names,
        )

    def _collect_defined_type_names(self, document: DocumentNode) -> set[str]:
        type_names: set[str] = set()
        for definition in document.definitions:
            if isinstance(definition, TYPE_DEFINITION_NODE_TYPES):
                type_names.add(definition.name.value)
        return type_names

    def _prefix_conflicting_type_names(
        self,
        schema_document: DependencySchemaDocument,
        conflicting_type_names: set[str],
    ) -> DependencySchemaDocument:
        conflicting_document_type_names = schema_document.defined_type_names.intersection(conflicting_type_names)
        if not conflicting_document_type_names:
            return schema_document

        prefix = sanitize_prefix(schema_document.metadata.preferred_prefix or schema_document.metadata.id)
        rename_by_type_name = {type_name: f"{prefix}_{type_name}" for type_name in conflicting_document_type_names}
        transformed_document = cast(
            DocumentNode, visit(schema_document.document, DependencyTypePrefixVisitor(rename_by_type_name))
        )
        defined_type_names = frozenset(self._collect_defined_type_names(transformed_document))
        return DependencySchemaDocument(
            metadata=schema_document.metadata,
            document=transformed_document,
            defined_type_names=defined_type_names,
        )

    def _find_duplicate_defined_type_names(self, schema_documents: list[DependencySchemaDocument]) -> set[str]:
        seen_type_names: set[str] = set()
        duplicate_type_names: set[str] = set()
        for schema_document in schema_documents:
            for type_name in schema_document.defined_type_names:
                if type_name in seen_type_names:
                    duplicate_type_names.add(type_name)
                seen_type_names.add(type_name)
        return duplicate_type_names
