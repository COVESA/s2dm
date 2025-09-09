from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from graphql import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    get_named_type,
)
from rdflib import RDF, RDFS, SH, XSD, BNode, Graph, Literal, Namespace, Node, URIRef
from rdflib.collection import Collection

from s2dm import log
from s2dm.exporters.utils.directive import get_argument_content, has_given_directive
from s2dm.exporters.utils.extraction import get_all_object_types
from s2dm.exporters.utils.field import Cardinality, FieldCase, get_cardinality, get_field_case_extended, print_field_sdl
from s2dm.exporters.utils.graphql_type import is_introspection_or_root_type
from s2dm.exporters.utils.instance_tag import expand_instance_tag, get_instance_tag_object, has_valid_instance_tag_field
from s2dm.exporters.utils.schema import load_schema_with_naming

SUPPORTED_FIELD_CASES = {
    FieldCase.DEFAULT,
    FieldCase.NON_NULL,
    FieldCase.SET,
    FieldCase.SET_NON_NULL,
}


@dataclass
class Namespaces:
    shapes: Namespace
    shapes_prefix: Namespace
    model: Namespace
    model_prefix: Namespace


# Datatype mapping from GraphQL to XSD
GRAPHQL_SCALAR_TO_XSD = {"Int": "integer", "Float": "float", "String": "string", "Boolean": "boolean", "ID": "string"}


def get_xsd_datatype(scalar: GraphQLScalarType) -> URIRef:
    return XSD[GRAPHQL_SCALAR_TO_XSD[scalar.name]]


def add_comment_to_property_node(field: GraphQLField, property_node: BNode, graph: Graph) -> None:
    """Add comment metadata to a property node if it exists."""
    comment = get_argument_content(field, "metadata", "comment")
    if comment and comment != {}:
        _ = graph.add((property_node, RDFS.comment, Literal(comment)))


def translate_to_shacl(
    schema_path: Path,
    shapes_namespace: str,
    shapes_namespace_prefix: str,
    model_namespace: str,
    model_namespace_prefix: str,
    naming_config: dict[str, Any] | None = None,
) -> Graph:
    """Translate a GraphQL schema to SHACL."""
    namespaces = Namespaces(
        Namespace(shapes_namespace),
        Namespace(shapes_namespace_prefix),
        Namespace(model_namespace),
        Namespace(model_namespace_prefix),
    )
    schema = load_schema_with_naming(schema_path, naming_config)
    graph = Graph()
    graph.bind(namespaces.shapes_prefix, namespaces.shapes)
    graph.bind(namespaces.model_prefix, namespaces.model)

    object_types = get_all_object_types(schema)
    log.debug(f"Object types: {object_types}")

    for object_type in object_types:
        if is_introspection_or_root_type(object_type.name):
            log.debug(f"Skipping internal object type '{object_type.name}'.")
            continue
        if has_given_directive(object_type, "instanceTag"):
            log.debug(f"Skipping object type '{object_type.name}' with directive 'instanceTag'.")
            continue
        process_object_type(namespaces, object_type, graph, schema, naming_config)

    return graph


def process_object_type(
    namespaces: Namespaces,
    object_type: GraphQLObjectType,
    graph: Graph,
    schema: GraphQLSchema,
    naming_config: dict[str, Any] | None = None,
) -> None:
    """Process a GraphQL object type and generate the corresponding SHACL triples."""
    log.info(f"Processing object type '{object_type.name}'.")
    shape_node = namespaces.shapes[object_type.name]
    _ = graph.add((shape_node, RDF.type, SH.NodeShape))
    _ = graph.add((shape_node, SH.name, Literal(object_type.name)))
    _ = graph.add((shape_node, SH.targetClass, namespaces.model[object_type.name]))
    if object_type.description:
        _ = graph.add((shape_node, SH.description, Literal(object_type.description)))

    for field_name, field in object_type.fields.items():
        process_field(namespaces, field_name, field, shape_node, graph, schema, naming_config)


def create_property_shape_with_literal(
    namespaces: Namespaces,
    field_name: str,
    field: GraphQLField,
    shape_node: URIRef,
    graph: Graph,
    value_cardinality: Cardinality | None = None,
    enum_values: list[str] | None = None,
) -> None:
    scalar_type = get_named_type(field.type)
    if not isinstance(scalar_type, GraphQLScalarType) and not isinstance(scalar_type, GraphQLEnumType):
        raise ValueError(f"Expected GraphQLScalarType or GraphQLEnumType, got {type(scalar_type).__name__}")
    property_path = namespaces.model[f"{field_name}"]
    property_node = BNode()
    _ = graph.add((shape_node, SH.property, property_node))
    _ = graph.add((property_node, SH.name, Literal(field_name)))
    _ = graph.add((property_node, SH.path, property_path))
    _ = graph.add((property_node, SH.nodeKind, SH.Literal))

    datatype = get_xsd_datatype(scalar_type) if isinstance(scalar_type, GraphQLScalarType) else XSD.string

    _ = graph.add((property_node, SH.datatype, datatype))

    if value_cardinality:
        if value_cardinality.min:
            _ = graph.add((property_node, SH.minCount, Literal(value_cardinality.min, datatype=XSD.integer)))
        if value_cardinality.max:
            _ = graph.add((property_node, SH.maxCount, Literal(value_cardinality.max, datatype=XSD.integer)))

    if enum_values is not None:
        # Create an RDF Collection for the enum values
        enum_list_node = BNode()
        _ = graph.add((property_node, SH["in"], enum_list_node))
        enum_literals = [Literal(val) for val in enum_values]
        _ = Collection(graph, enum_list_node, cast(list[Node], enum_literals))

    if field.description:
        _ = graph.add((property_node, SH.description, Literal(field.description)))

    add_comment_to_property_node(field, property_node, graph)


def create_property_shape_with_iri(
    namespaces: Namespaces,
    field_name: str,
    field: GraphQLField,
    shape_node: URIRef,
    graph: Graph,
    value_cardinality: Cardinality | None = None,
) -> None:
    unwrapped_output_type = get_named_type(field.type)  # GraphQL type without modifiers [] or !

    property_node = BNode()
    property_path = namespaces.model["has" + unwrapped_output_type.name]
    _ = graph.add((shape_node, SH.property, property_node))
    _ = graph.add((property_node, SH.name, Literal(field_name)))
    _ = graph.add((property_node, SH.path, property_path))
    _ = graph.add((property_node, SH.nodeKind, SH.IRI))
    _ = graph.add((property_node, SH.node, namespaces.shapes[unwrapped_output_type.name]))
    _ = graph.add((property_node, SH["class"], namespaces.model[unwrapped_output_type.name]))
    if value_cardinality:
        if value_cardinality.min:
            _ = graph.add((property_node, SH.minCount, Literal(value_cardinality.min, datatype=XSD.integer)))
        if value_cardinality.max:
            _ = graph.add((property_node, SH.maxCount, Literal(value_cardinality.max, datatype=XSD.integer)))

    if field.description:
        _ = graph.add((property_node, SH.description, Literal(field.description)))

    add_comment_to_property_node(field, property_node, graph)


def process_field(
    namespaces: Namespaces,
    field_name: str,
    field: GraphQLField,
    shape_node: URIRef,
    graph: Graph,
    schema: GraphQLSchema,
    naming_config: dict[str, Any] | None = None,
) -> None:
    """Process a field of a GraphQL object type and generate the corresponding SHACL triples."""
    log.info(f"Processing field... '{print_field_sdl(field)}'")
    field_case = get_field_case_extended(field)
    log.debug(f"Field case: {field_case}")
    if field_case not in SUPPORTED_FIELD_CASES:
        log.warning(
            f"""Field case '{field_case.name}' is currently not supported by this exporter.
            Supported field cases are: {[case.name for case in SUPPORTED_FIELD_CASES]}.
            Skipping field '{field_name}'."""
        )
        return None
    elif field_name == "instanceTag":
        log.debug(
            f"Skipping field '{field_name}'. It is a reserved field and its likely already "
            + "processed as expanded instances.",
        )
        return None
    else:
        spec_cardinality = get_cardinality(field)
        value_cardinality = spec_cardinality if spec_cardinality else field_case.value.value_cardinality
        unwrapped_field_type = get_named_type(field.type)  # GraphQL type without modifiers [] or !
        log.debug(f"Unwrapped field type: {unwrapped_field_type}")

        if field_case == FieldCase.DEFAULT or field_case == FieldCase.NON_NULL:
            # Output type has no List type modifier.
            if isinstance(unwrapped_field_type, GraphQLScalarType):
                create_property_shape_with_literal(
                    namespaces=namespaces,
                    field_name=field_name,
                    field=field,
                    shape_node=shape_node,
                    graph=graph,
                    value_cardinality=value_cardinality,
                )
            elif isinstance(unwrapped_field_type, GraphQLEnumType):
                create_property_shape_with_literal(
                    namespaces,
                    field_name,
                    field,
                    shape_node,
                    graph,
                    value_cardinality,
                    enum_values=list(unwrapped_field_type.values.keys()),
                )
            elif isinstance(unwrapped_field_type, GraphQLObjectType):
                create_property_shape_with_iri(
                    namespaces=namespaces,
                    field_name=field_name,
                    field=field,
                    shape_node=shape_node,
                    graph=graph,
                    value_cardinality=value_cardinality,
                )

        elif field_case == FieldCase.SET or field_case == FieldCase.SET_NON_NULL:
            # Output type has a List type modifier and a @noDuplicates directive.
            if isinstance(unwrapped_field_type, GraphQLScalarType):
                create_property_shape_with_literal(
                    namespaces=namespaces,
                    field_name=field_name,
                    field=field,
                    shape_node=shape_node,
                    graph=graph,
                    value_cardinality=value_cardinality,
                )
            elif isinstance(unwrapped_field_type, GraphQLEnumType):
                create_property_shape_with_literal(
                    namespaces,
                    field_name,
                    field,
                    shape_node,
                    graph,
                    value_cardinality,
                    enum_values=list(unwrapped_field_type.values.keys()),
                )
            elif isinstance(unwrapped_field_type, GraphQLObjectType):
                if has_valid_instance_tag_field(object_type=unwrapped_field_type, schema=schema):
                    instance_tag_object = get_instance_tag_object(unwrapped_field_type, schema)
                    if instance_tag_object is not None:
                        expanded_tags = expand_instance_tag(instance_tag_object, naming_config)
                        for tag in expanded_tags:
                            create_property_shape_with_iri(
                                namespaces=namespaces,
                                field_name=f"{unwrapped_field_type.name}.{tag}",
                                field=field,
                                shape_node=shape_node,
                                graph=graph,
                                value_cardinality=value_cardinality,
                            )
                else:
                    create_property_shape_with_iri(
                        namespaces=namespaces,
                        field_name=field_name,
                        field=field,
                        shape_node=shape_node,
                        graph=graph,
                        value_cardinality=value_cardinality,
                    )
            else:
                raise ValueError(f"Unsupported case for field '{field_name}'.")
