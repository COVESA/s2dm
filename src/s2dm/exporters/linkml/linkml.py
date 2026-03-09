from s2dm import log
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema

from .transformer import LinkmlTransformer


def transform(
    annotated_schema: AnnotatedSchema,
    schema_id: str,
    schema_name: str,
    default_prefix: str,
    default_prefix_url: str,
) -> str:
    """Transform an annotated GraphQL schema into LinkML schema YAML."""
    log.info(f"Transforming GraphQL schema to LinkML with {len(annotated_schema.schema.type_map)} types")

    transformer = LinkmlTransformer(
        annotated_schema,
        schema_id,
        schema_name,
        default_prefix,
        default_prefix_url,
    )
    linkml_schema = transformer.transform()

    log.info("Successfully converted GraphQL schema to LinkML")

    return linkml_schema


def translate_to_linkml(
    annotated_schema: AnnotatedSchema,
    schema_id: str,
    schema_name: str,
    default_prefix: str,
    default_prefix_url: str,
) -> str:
    """Translate an annotated GraphQL schema into LinkML schema YAML."""
    return transform(
        annotated_schema,
        schema_id,
        schema_name,
        default_prefix,
        default_prefix_url,
    )
