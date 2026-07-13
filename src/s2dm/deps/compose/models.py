from dataclasses import dataclass

from graphql import DocumentNode

from s2dm.deps.models import DependencyMetadata


@dataclass(frozen=True)
class DependencySchemaInput:
    """Loaded dependency schema content input for dependency build."""

    schema_content: str
    metadata: DependencyMetadata


@dataclass(frozen=True)
class DependencyTypeNameConflict:
    """GraphQL type name defined by multiple dependencies."""

    type_name: str
    dependencies_metadata: tuple[DependencyMetadata, ...]


@dataclass(frozen=True)
class DependencySchemaDocument:
    """Parsed dependency schema document with metadata needed for auto-prefixing."""

    metadata: DependencyMetadata
    document: DocumentNode
    defined_type_names: frozenset[str]
