import logging
from pathlib import Path

import click
import yaml
from graphql import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    get_named_type,
)

from tools.utils import (
    FieldCase,
    get_all_expanded_instance_tags,
    get_all_named_types,
    get_all_object_types,
    get_all_objects_with_directive,
    get_instance_tag_dict,
    get_instance_tag_object,
    has_directive,
    load_schema,
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
    all_object_types = get_all_object_types(named_types)
    logging.debug(f"Object types: {all_object_types}")
    instance_tag_objects = get_all_objects_with_directive(all_object_types, "instanceTag")
    # Remove instance tag objects from object_types
    object_types = [obj for obj in all_object_types if obj not in instance_tag_objects]
    logging.debug(f"Instance Tag Objects: {instance_tag_objects}")
    global INSTANCE_TAGS
    INSTANCE_TAGS = get_all_expanded_instance_tags(schema)
    nested_types = []  # List to collect nested structures to reconstruct the path
    yaml_dict = {}
    for object_type in object_types:
        if object_type.name == "Query":
            logging.debug("Skipping Query object type.")
            continue
        
        # Add a VSS branch structure for the object type
        if object_type.name not in yaml_dict:
            yaml_dict.update(process_object_type(object_type, schema))  
        else:
            # TODO: Check if the processed object type is already in the yaml_dict
            logging.debug(f"Object type '{object_type.name}' already exists in the YAML dictionary. Skipping.")
        # Process the fields of the object type
        for field_name, field in object_type.fields.items():
            #if is_valid_instance_tag_field(field, schema):
            #    logging.debug(f"Skipping field '{field_name}' in object type '{object_type.name}' as it is a valid instance tag field.")
            #    continue  # Skip instance tag fields
            # Add a VSS leaf structure for the field
            field_result = process_field(field_name, field, object_type, schema, nested_types)
            if field_result is not None:
                yaml_dict.update(field_result)
            else:
                logging.debug(f"Skipping field '{field_name}' in object type '{object_type.name}' as process_field returned None.")

    logging.debug(f"Nested types: {nested_types}")
    reconstructed_paths = reconstruct_paths(nested_types)
    logging.debug(f"Reconstructed {reconstructed_paths}")
    # TODO: Think of splitting the yaml dump into two: one for object types and one for fields. Reason: to maintain the same order of the keys in the fields, and also to structure the export better and sorted for easier control of the output.    
    for key in list(yaml_dict.keys()):
        first_word = key.split('.')[0]
        for path in reconstructed_paths:
            path_parts = path.split('.')
            if first_word == path_parts[-1]:
                new_key = '.'.join(path_parts[:-1] + [key])
                yaml_dict[new_key] = yaml_dict.pop(key)
                break
    return yaml.dump(yaml_dict, default_flow_style=False, Dumper=CustomDumper, sort_keys=True)


def process_object_type(object_type: GraphQLObjectType, schema: GraphQLSchema) -> dict:
    """Process a GraphQL object type and generate the corresponding YAML."""
    logging.info(f"Processing object type '{object_type.name}'.")

    obj_dict = {
        "type": "branch",
    }
    if object_type.description:
        obj_dict["description"] = object_type.description

    instance_tag_object = get_instance_tag_object(object_type, schema)
    if instance_tag_object:
        logging.debug(f"Object type '{object_type.name}' has instance tag '{instance_tag_object}'.")        
        obj_dict["instances"] = list(get_instance_tag_dict(instance_tag_object).values())
    else:
        logging.debug(f"Object type '{object_type.name}' does not have an instance tag.")
        
    return {object_type.name: obj_dict}

def process_field(field_name: str, field: GraphQLField, object_type: GraphQLObjectType, schema: GraphQLSchema, 
                  nested_types: list) -> dict:
    """Process a GraphQL field and generate the corresponding YAML."""
    logging.info(f"Processing field '{field_name}'.")
    concat_field_name = f"{object_type.name}.{field_name}"

    output_type = get_named_type(field.type)
    if isinstance(output_type, GraphQLScalarType):
        field_dict = {
            "description": field.description if field.description else "",
            "datatype": SCALAR_DATATYPE_MAP[output_type.name]
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

        if has_directive(field, "metadata"):
            metadata_directive = next(
                (directive for directive in field.ast_node.directives if directive.name.value == "metadata"), 
                None
            )
            
            metadata_args = {}
            for arg in metadata_directive.arguments:
                metadata_args[arg.name.value] = arg.value.value

            comment = metadata_args.get("comment")
            vss_type = metadata_args.get("vssType")
            if comment:
                field_dict["comment"] = comment
            if vss_type:
                field_dict["type"] = vss_type

        return {concat_field_name: field_dict}
    elif isinstance(output_type, GraphQLObjectType) and field_name != "instanceTag":
        # Collect nested structures
        #nested_types.append(f"{object_type.name}.{output_type}({field_name})")
        nested_types.append((object_type.name, output_type.name))
        logging.debug(f"Nested structure found: {object_type.name}.{output_type}(for field {field_name})")
        return process_object_type(get_named_type(field.type), schema)  # Nested object type, process it recursively
    elif isinstance(output_type, GraphQLEnumType):
        field_dict = {
            "description": field.description if field.description else "",
            "datatype": "string",  # TODO: Consider that VSS allows any datatype for enums.
            "allowed": [value.value for value in field.type.values.values()]
        }
        return {concat_field_name: field_dict}
        
    else:
        logging.debug(f"Skipping (in the output YAML) the field '{field_name}' with output type '{type(field.type).__name__}'.")

def reconstruct_paths(nested_types):
    # Dictionary to store the graph structure
    graph = {}
    for parent, child in nested_types:
        if parent not in graph:
            graph[parent] = []
        graph[parent].append(child)

    # Identify all potential root nodes (nodes that are parents but not children)
    all_parents = set(parent for parent, _ in nested_types)
    all_children = set(child for _, child in nested_types)
    root_nodes = all_parents - all_children

    # Set to store unique paths
    unique_paths = set()

    # Recursive function to build paths
    def build_paths(current, path):
        # Add the current path to the unique paths set
        unique_paths.add(".".join(path))

        # If the current type has children, recurse
        if current in graph:
            for child in graph[current]:
                build_paths(child, path + [child])

    # Start building paths from each root node
    for root in root_nodes:
        build_paths(root, [root])

    # Return the sorted unique paths
    return sorted(unique_paths)


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
