import logging
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
from rdflib import BNode, Graph, Literal
import yaml

from tools.utils import (
    FieldCase,
    get_all_expanded_instance_tags,
    get_all_named_types,
    get_all_object_types,
    get_all_objects_with_directive,
    get_field_case_extended,
    get_instance_tag_dict,
    get_instance_tag_object,
    has_directive,
    has_valid_instance_tag_field,
    is_valid_instance_tag_field,
    load_schema,
    print_field_sdl,
)

SUPPORTED_FIELD_CASES = {
    FieldCase.DEFAULT,
    FieldCase.NON_NULL,
    FieldCase.LIST,
    FieldCase.LIST_NON_NULL,
    FieldCase.NON_NULL_LIST,
    FieldCase.NON_NULL_LIST_NON_NULL,
}
logging.debug(f"export vspec supports these field cases:\n{SUPPORTED_FIELD_CASES}")

INSTANCE_TAGS = None

SCALAR_DATATYPE_MAP = {
    # Built-in scalar types
    "Int": "int32",
    "Float": "float",
    "String": "string",
    "Boolean": "boolean",
    "ID": "string",
    # Custom scalar types
    "Int8": "int8",
    "UInt8": "uint8",
    "Int16": "int16",
    "UInt16": "uint16",
    "UInt32": "uint32",
    "Int64": "int64",
    "UInt64": "uint64",    
}

"""
TODO: Replace the mapping with the classes of graphql-core and the actual datatypes from the VSS tools.
SCALAR_DATATYPE_MAP = {
    # Built-in scalar types
    GraphQLInt: Datatypes.INT32[0],
    GraphQLFloat: Datatypes.FLOAT[0],
    GraphQLString: Datatypes.STRING[0],
    GraphQLBoolean: Datatypes.BOOLEAN[0],
    GraphQLID: Datatypes.STRING[0],
    # TODO: Add custom scalar types
    ?: Datatypes.INT8[0],
    ?: Datatypes.UINT8[0],
    ?: Datatypes.INT16[0],
    ?: Datatypes.UINT16[0],
    ?: Datatypes.UINT32[0],
    ?: Datatypes.INT64[0],
    ?: Datatypes.UINT64[0],
}
"""

class CustomDumper(yaml.Dumper):
    """Custom YAML dumper to add extra line breaks at the top level."""
    def write_line_break(self, data=None):
        super().write_line_break(data)
        if len(self.indents) == 1:  # Only add extra line break at the top level
            super().write_line_break()
    
    def represent_list(self, data):
        # Check if the list is an inner list (nested list)
        if all(isinstance(item, str) for item in data):
            # Serialize inner lists in flow style
            return super().represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)
        else:
            # Serialize outer lists in block style
            return super().represent_sequence('tag:yaml.org,2002:seq', data, flow_style=False)

# Register the custom representer for lists
CustomDumper.add_representer(list, CustomDumper.represent_list)

def translate_to_vspec(schema_path: Path) -> str:
    """Translate a GraphQL schema to YAML."""
    schema = load_schema(schema_path)
    
    named_types = get_all_named_types(schema)
    object_types = get_all_object_types(named_types)
    logging.debug(f"Object types: {object_types}")
    instance_tag_objects = get_all_objects_with_directive(object_types, "instanceTag")
    logging.debug(f"Instance Tag Objects: {instance_tag_objects}")
    global INSTANCE_TAGS
    INSTANCE_TAGS = get_all_expanded_instance_tags(schema)
    logging.debug(f"Expanded tags from spec: {INSTANCE_TAGS}")

    yaml_dict = {}
    for object_type in object_types:
        if object_type.name == "Query":
            logging.debug("Skipping Query object type.")
            continue
        if object_type in instance_tag_objects:
            logging.debug(f"Skipping object type '{object_type.name}' with directive 'instanceTag'.")
            continue

        # Add a VSS branch structure for the object type
        yaml_dict.update(process_object_type(object_type, schema))
        
        # Process the fields of the object type
        for field_name, field in object_type.fields.items():
            if is_valid_instance_tag_field(field, schema):
                continue  # Skip instance tag fields
            yaml_dict.update(process_field(field_name, field, object_type, schema))

    # TODO: Think of splitting the yaml dump into two: one for object types and one for fields. Reason: to maintain the same order of the keys in the fields, and also to structure the export better and sorted for easier control of the output.    
    return yaml.dump(yaml_dict, default_flow_style=False, Dumper=CustomDumper, sort_keys=True)


def process_object_type(object_type: GraphQLObjectType, schema: GraphQLSchema) -> dict:
    """Process a GraphQL object type and generate the corresponding YAML."""
    logging.info(f"Processing object type '{object_type.name}'.")

    obj_dict = {
        "type": "Branch",
    }
    if object_type.description:
        obj_dict["description"] = object_type.description

    instance_tag_object = get_instance_tag_object(object_type, schema)
    if instance_tag_object:
        logging.debug(f"Object type '{object_type.name}' has instance tag '{instance_tag_object}'.")
        logging.debug(f"Instance tags are: {INSTANCE_TAGS}")
        
        #obj_dict["instances"] = INSTANCE_TAGS[instance_tag_object]
        
        obj_dict["instances"] = list(get_instance_tag_dict(instance_tag_object).values())
            
    return {object_type.name: obj_dict}

def process_field(field_name: str, field: GraphQLField, object_type: GraphQLObjectType, schema: GraphQLSchema) -> dict:
    """Process a GraphQL field and generate the corresponding YAML."""
    logging.info(f"Processing field '{field_name}'.")
    concat_field_name = f"{object_type.name}.{field_name}"

    if isinstance(field.type, GraphQLScalarType):
        field_dict = {
            "type": "Leaf",
            "description": field.description if field.description else "",
            "datatype": SCALAR_DATATYPE_MAP[field.type.name]
        }
        # TODO: Fix numbers that are appearing with quotes as strings.
        if has_directive(field, "range"):
            range_directive = field.ast_node.directives[0]
            min_arg = next((arg.value.value for arg in range_directive.arguments if arg.name.value == "min"), None)
            max_arg = next((arg.value.value for arg in range_directive.arguments if arg.name.value == "max"), None)
            if min_arg is not None or max_arg is not None:
                field_dict["min"] = min_arg
                field_dict["max"] = max_arg

        # TODO: Map the unit name to the VSS unit name. i.e., SCREAMMING_SNAKE_CASE used in graphql to abbreviated vss unit name.
        if "unit" in field.args:
            unit_arg = field.args["unit"].default_value
            if unit_arg is not None:
                field_dict["unit"] = unit_arg
        return {concat_field_name: field_dict}
    else:
        return process_object_type(get_named_type(field.type), schema)


@click.command()
@click.argument("schema", type=click.Path(exists=True), required=True)
@click.argument("output", type=click.Path(dir_okay=False, writable=True, path_type=Path), required=True)
def main(
    schema: Path,
    output: Path,
):
    result = translate_to_vspec(schema, output)
    logging.info(f"Result:\n{result}")

if __name__ == "__main__":
    main()
