from dataclasses import dataclass
from pathlib import Path
from typing import cast

from graphql import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLObjectType,
    GraphQLScalarType,
    get_named_type,
    is_list_type,
)
from rdflib import RDF, SH, XSD, BNode, Graph, Literal, Namespace, Node, URIRef
from rdflib.collection import Collection

from s2dm import log
from s2dm.exporters.utils import (
    Cardinality,
    FieldCase,
    get_all_expanded_instance_tags,
    get_all_named_types,
    get_all_object_types,
    get_all_objects_with_directive,
    get_cardinality,
    get_field_case_extended,
    has_directive,
    load_schema,
    print_field_sdl,
)

SUPPORTED_FIELD_CASES = {
    FieldCase.DEFAULT,
    FieldCase.NON_NULL,
    FieldCase.SET,
    FieldCase.SET_NON_NULL,
}

InstanceTags = dict[GraphQLObjectType, list[str]] | None


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


def translate_to_shacl(
    schema_path: Path,
    shapes_namespace: str,
    shapes_namespace_prefix: str,
    model_namespace: str,
    model_namespace_prefix: str,
) -> Graph:
    """Translate a GraphQL schema to SHACL."""
    namespaces = Namespaces(
        Namespace(shapes_namespace),
        Namespace(shapes_namespace_prefix),
        Namespace(model_namespace),
        Namespace(model_namespace_prefix),
    )
    schema = load_schema(schema_path)
    graph = Graph()
    graph.bind("sh", SH)
    graph.bind("xsd", XSD)
    graph.bind(namespaces.shapes_prefix, namespaces.shapes)
    graph.bind(namespaces.model_prefix, namespaces.model)

    named_types = get_all_named_types(schema)
    object_types = get_all_object_types(named_types)
    log.debug(f"Object types: {object_types}")
    instance_tag_objects = get_all_objects_with_directive(object_types, "instanceTag")
    log.debug(f"Instance Tag Objects: {instance_tag_objects}")
    instance_tags = get_all_expanded_instance_tags(schema)
    log.debug(f"Expanded tags from spec: {instance_tags}")

    for object_type in object_types:
        if object_type.name == "Query":
            log.debug("Skipping Query object type.")
            continue
        if has_directive(object_type, "instanceTag"):
            log.debug(f"Skipping object type '{object_type.name}' with directive 'instanceTag'.")
            continue
        process_object_type(namespaces, object_type, graph, instance_tags)

    return graph


def process_object_type(
    namespaces: Namespaces,
    object_type: GraphQLObjectType,
    graph: Graph,
    instance_tags: InstanceTags,
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
        process_field(namespaces, field_name, field, shape_node, graph, instance_tags)


def get_instance_tag_object(object: GraphQLObjectType) -> GraphQLObjectType | None:
    """Get the object type of the instance tag (if exists)."""
    if "instanceTag" in object.fields:
        instance_tag_field = object.fields["instanceTag"]
        instance_tag_output_type = get_named_type(instance_tag_field.type)
        if isinstance(instance_tag_output_type, GraphQLObjectType):
            return instance_tag_output_type
        else:
            # TODO: Move this validation step to a validation function for instance tags.
            raise ValueError(f"Instance tag field '{instance_tag_output_type}' is not an object type.")
    return None


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


def process_field(
    namespaces: Namespaces,
    field_name: str,
    field: GraphQLField,
    shape_node: URIRef,
    graph: Graph,
    instance_tags: InstanceTags,
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
        return
    else:
        if field_name == "instanceTag":
            log.debug(
                f"Skipping field '{field_name}'. It is a reserved field and its likely already ",
                "processed as expanded instances.",
            )
            return
        else:
            spec_cardinality = get_cardinality(field)
            value_cardinality = spec_cardinality if spec_cardinality else field_case.value.value_cardinality
            unwrapped_field_type = get_named_type(field.type)  # GraphQL type without modifiers [] or !
            log.debug(f"Unwrapped field type: {unwrapped_field_type}")
            if isinstance(unwrapped_field_type, GraphQLScalarType):
                create_property_shape_with_literal(
                    namespaces=namespaces,
                    field_name=field_name,
                    field=field,
                    shape_node=shape_node,
                    graph=graph,
                    value_cardinality=value_cardinality,
                )
            elif is_list_type(field.type):
                if isinstance(unwrapped_field_type, GraphQLObjectType):
                    instance_tag_object = get_instance_tag_object(unwrapped_field_type)
                    if not instance_tag_object:
                        create_property_shape_with_iri(
                            namespaces=namespaces,
                            field_name=field_name,
                            field=field,
                            shape_node=shape_node,
                            graph=graph,
                            value_cardinality=value_cardinality,
                        )
                        return
                    else:
                        if instance_tags is None:
                            raise ValueError("instance_tags not initialized.")
                        for tag in instance_tags:
                            create_property_shape_with_iri(
                                namespaces=namespaces,
                                field_name=f"{unwrapped_field_type.name}.{tag}",
                                field=field,
                                # unwrapped_field_type.name,
                                shape_node=shape_node,
                                graph=graph,
                                value_cardinality=value_cardinality,
                            )
                        return
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
            else:
                create_property_shape_with_iri(
                    namespaces=namespaces,
                    field_name=field_name,
                    field=field,
                    shape_node=shape_node,
                    graph=graph,
                    value_cardinality=value_cardinality,
                )
