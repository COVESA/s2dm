from dataclasses import dataclass, field

from graphql import GraphQLField, GraphQLSchema


@dataclass
class TypeMetadata:
    source: str | None
    is_intermediate_type: bool


@dataclass
class FieldMetadata:
    resolved_names: list[str]
    resolved_type: str
    is_expanded: bool
    original_field: GraphQLField | None = None
    instances: list[list[str]] = field(default_factory=list)


@dataclass
class AnnotatedSchema:
    schema: GraphQLSchema
    type_metadata: dict[str, TypeMetadata] = field(default_factory=dict)
    field_metadata: dict[tuple[str, str], FieldMetadata] = field(default_factory=dict)
