from pathlib import Path

import click
from graphql import (
    GraphQLField,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    get_named_type,
    is_list_type,
)
from rdflib import RDF, BNode, Graph, Literal, Namespace

from s2dm import log
from s2dm.exporters.utils import (
    FieldCase,
    get_all_expanded_instance_tags,
    get_all_named_types,
    get_all_object_types,
    get_all_objects_with_directive,
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

# Namespaces and prefixes
SH = Namespace("http://www.w3.org/ns/shacl#")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

SHAPES_NAMESPACE = None
SHAPES_NAMESPACE_PREFIX = None
MODEL_NAMESPACE = None
MODEL_NAMESPACE_PREFIX = None

INSTANCE_TAGS = None

# Datatype mapping from GraphQL to XSD
GRAPHQL_SCALAR_TO_XSD = {"Int": "integer", "Float": "float", "String": "string", "Boolean": "boolean", "ID": "string"}


def get_xsd_datatype(scalar: GraphQLScalarType) -> str:
    return XSD[GRAPHQL_SCALAR_TO_XSD[scalar.name]]


def translate_to_shacl(
    schema_path: Path,
    shapes_namespace: str,
    shapes_namespace_prefix: str,
    model_namespace: str,
    model_namespace_prefix: str,
) -> Graph:
    """Translate a GraphQL schema to SHACL."""
    # Set the global variables for the namespaces to avoid passing them as arguments multiple times
    global SHAPES_NAMESPACE, SHAPES_NAMESPACE_PREFIX, MODEL_NAMESPACE, MODEL_NAMESPACE_PREFIX, INSTANCE_TAGS
    SHAPES_NAMESPACE = Namespace(shapes_namespace)
    SHAPES_NAMESPACE_PREFIX = Namespace(shapes_namespace_prefix)
    MODEL_NAMESPACE = Namespace(model_namespace)
    MODEL_NAMESPACE_PREFIX = Namespace(model_namespace_prefix)

    schema = load_schema(schema_path)
    graph = Graph()
    graph.bind("sh", SH)
    graph.bind("xsd", XSD)
    graph.bind(SHAPES_NAMESPACE_PREFIX, SHAPES_NAMESPACE)
    graph.bind(MODEL_NAMESPACE_PREFIX, MODEL_NAMESPACE)

    named_types = get_all_named_types(schema)
    object_types = get_all_object_types(named_types)
    log.debug(f"Object types: {object_types}")
    instance_tag_objects = get_all_objects_with_directive(object_types, "instanceTag")
    log.debug(f"Instance Tag Objects: {instance_tag_objects}")
    INSTANCE_TAGS = get_all_expanded_instance_tags(schema)
    log.debug(f"Expanded tags from spec: {INSTANCE_TAGS}")

    for object_type in object_types:
        if object_type.name == "Query":
            log.debug("Skipping Query object type.")
            continue
        if has_directive(object_type, "instanceTag"):
            log.debug(f"Skipping object type '{object_type.name}' with directive 'instanceTag'.")
            continue
        process_object_type(object_type, graph, schema)

    return graph


def process_object_type(object_type: GraphQLObjectType, graph: Graph, schema: GraphQLSchema):
    """Process a GraphQL object type and generate the corresponding SHACL triples."""
    log.info(f"Processing object type '{object_type.name}'.")
    shape_node = SHAPES_NAMESPACE[object_type.name]
    graph.add((shape_node, RDF.type, SH.NodeShape))
    graph.add((shape_node, SH.name, Literal(object_type.name)))
    graph.add((shape_node, SH.targetClass, MODEL_NAMESPACE[object_type.name]))
    if object_type.description:
        graph.add((shape_node, SH.description, Literal(object_type.description)))

    for field_name, field in object_type.fields.items():
        process_field(field_name, field, shape_node, graph, schema)


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


def get_expanded_instances(object: GraphQLObjectType) -> list:
    pass


def create_property_shape_with_literal(
    field_name, field: GraphQLField, shape_node, graph: Graph, value_cardinality=None
):
    property_path = MODEL_NAMESPACE[f"{field_name}"]
    property_node = BNode()
    graph.add((shape_node, SH.property, property_node))
    graph.add((property_node, SH.name, Literal(field_name)))
    graph.add((property_node, SH.path, property_path))
    graph.add((property_node, SH.nodeKind, SH.Literal))
    graph.add((property_node, SH.datatype, get_xsd_datatype(get_named_type(field.type))))
    if value_cardinality.min:
        graph.add((property_node, SH.minCount, Literal(value_cardinality.min, datatype=XSD.integer)))
    if value_cardinality.max:
        graph.add((property_node, SH.maxCount, Literal(value_cardinality.max, datatype=XSD.integer)))


def create_property_shape_with_iri(property_name, output_type_name, shape_node, graph: Graph, value_cardinality=None):
    property_node = BNode()
    property_path = MODEL_NAMESPACE["has"]
    graph.add((shape_node, SH.property, property_node))
    graph.add((property_node, SH.name, Literal(property_name)))
    graph.add((property_node, SH.path, property_path))
    graph.add((property_node, SH.nodeKind, SH.IRI))
    graph.add((property_node, SH.node, SHAPES_NAMESPACE[output_type_name]))
    graph.add((property_node, SH["class"], MODEL_NAMESPACE[output_type_name]))
    if value_cardinality.min:
        graph.add((property_node, SH.minCount, Literal(value_cardinality.min, datatype=XSD.integer)))
    if value_cardinality.max:
        graph.add((property_node, SH.maxCount, Literal(value_cardinality.max, datatype=XSD.integer)))


def process_field(field_name: str, field: GraphQLField, shape_node, graph: Graph, schema: GraphQLSchema):
    """Process a field of a GraphQL object type and generate the corresponding SHACL triples."""
    field_case = get_field_case_extended(field)

    # Log the field definition as it appears in the GraphQL SDL
    # field_sdl = get_sdl_str(field)
    log.info(f"Processing field... '{print_field_sdl(field)}'")
    log.debug(f"Field case: {field_case}")

    if field_case not in SUPPORTED_FIELD_CASES:
        log.warning(
            f"Field case '{field_case.name}' is currently not supported by this exporter.\n"
            f"Supported field cases are: {[case.name for case in SUPPORTED_FIELD_CASES]}"
        )
        log.info(f"Skipping field '{field_name}'")
        return
    else:
        if (
            field_name == "instanceTag"
        ):  # TODO: Consider handling the instanceTag field differently instead of skipping it
            log.debug(
                f"Skipping field '{field_name}'. It is a reserved field and its likely already "
                f"processed as expanded instances."
            )
            return
        else:
            # TODO: Parse the min and max in the @cardinality directive, implement consistency checking first
            value_cardinality = field_case.value.value_cardinality

            unwrapped_field_type = get_named_type(field.type)  # GraphQL type without modifiers [] or !
            log.debug(f"Unwrapped field type: {unwrapped_field_type}")
            if isinstance(unwrapped_field_type, GraphQLScalarType):
                create_property_shape_with_literal(field_name, field, shape_node, graph, value_cardinality)
            elif is_list_type(field.type):
                instance_tag_object = get_instance_tag_object(unwrapped_field_type)
                if not instance_tag_object:
                    create_property_shape_with_iri(
                        unwrapped_field_type.name, unwrapped_field_type.name, shape_node, graph, value_cardinality
                    )
                    return
                else:
                    instance_tags = INSTANCE_TAGS[instance_tag_object]
                    for tag in instance_tags:
                        create_property_shape_with_iri(
                            f"{unwrapped_field_type.name}.{tag}",
                            unwrapped_field_type.name,
                            shape_node,
                            graph,
                            value_cardinality,
                        )
                    return
            else:
                create_property_shape_with_iri(
                    unwrapped_field_type.name, unwrapped_field_type.name, shape_node, graph, value_cardinality
                )


@click.command()
@click.argument("schema", type=click.Path(exists=True), required=True)
@click.argument("output", type=click.Path(dir_okay=False, writable=True, path_type=Path), required=True)
@click.argument("serialization_format", type=str, default="ttl")
@click.argument("shapes_namespace", type=str, default="http://example.org/shapes#")
@click.argument("shapes_namespace_prefix", type=str, default="shapes")
@click.argument("model_namespace", type=str, default="http://example.org/ontology#")
@click.argument("model_namespace_prefix", type=str, default="model")
def main(
    schema: Path,
    output: Path,
    serialization_format: str,
    shapes_namespace: str,
    shapes_namespace_prefix: str,
    model_namespace: str,
    model_namespace_prefix: str,
):
    shacl_graph = translate_to_shacl(
        schema, shapes_namespace, shapes_namespace_prefix, model_namespace, model_namespace_prefix
    )
    shacl_graph.serialize(destination=output, format=serialization_format)


if __name__ == "__main__":
    main()
