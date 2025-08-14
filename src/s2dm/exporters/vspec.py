from collections.abc import Iterable
from pathlib import Path
from typing import Any

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

from s2dm import log
from s2dm.exporters.utils import (
    FieldCase,
    get_all_expanded_instance_tags,
    get_all_object_types,
    get_all_objects_with_directive,
    get_instance_tag_dict,
    get_instance_tag_object,
    has_directive,
    load_schema_with_naming,
)

UNITS_DICT = {  # TODO: move to a separate file or use the vss tools to get the mapping directly from dynamic_units
    "MILLIMETER": "mm",
    "CENTIMETER": "cm",
    "METER": "m",
    "KILOMETER": "km",
    "INCH": "inch",
    "KILOMETER_PER_HOUR": "km/h",
    "METERS_PER_SECOND": "m/s",
    "METERS_PER_SECOND_SQUARED": "m/s^2",
    "CENTIMETERS_PER_SECOND_SQUARED": "cm/s^2",
    "MILLILITER": "ml",
    "LITER": "l",
    "CUBIC_CENTIMETERS": "cm^3",
    "DEGREE_CELSIUS": "celsius",
    "DEGREE": "degrees",
    "DEGREE_PER_SECOND": "degrees/s",
    "RADIANS_PER_SECOND": "rad/s",
    "WATT": "W",
    "KILOWATT": "kW",
    "HORSEPOWER": "PS",
    "KILOWATT_HOURS": "kWh",
    "GRAM": "g",
    "KILOGRAM": "kg",
    "POUND": "lbs",
    "VOLT": "V",
    "AMPERE": "A",
    "AMPERE_HOURS": "Ah",
    "MILLISECOND": "ms",
    "SECOND": "s",
    "MINUTE": "min",
    "HOUR": "h",
    "DAYS": "day",
    "WEEKS": "weeks",
    "MONTHS": "months",
    "YEARS": "years",
    "UNIX_TIMESTAMP": "unix-time",
    "ISO_8601": "iso8601",
    "MILLIBAR": "mbar",
    "PASCAL": "Pa",
    "KILOPASCAL": "kPa",
    "POUNDS_PER_SQUARE_INCH": "psi",
    "STARS": "stars",
    "GRAMS_PER_SECOND": "g/s",
    "GRAMS_PER_KILOMETER": "g/km",
    "KILOWATT_HOURS_PER_100_KILOMETERS": "kWh/100km",
    "WATT_HOUR_PER_KM": "Wh/km",
    "MILLILITER_PER_100_KILOMETERS": "ml/100km",
    "LITER_PER_100_KILOMETERS": "l/100km",
    "LITER_PER_HOUR": "l/h",
    "MILES_PER_GALLON": "mpg",
    "KILOMETERS_PER_LITER": "km/l",
    "NEWTON": "N",
    "KILO_NEWTON": "kN",
    "NEWTON_METER": "Nm",
    "REVOLUTIONS_PER_MINUTE": "rpm",
    "HERTZ": "Hz",
    "CYCLES_PER_MINUTE": "cpm",
    "BEATS_PER_MINUTE": "bpm",
    "RATIO": "ratio",
    "PERCENT": "percent",
    "NANO_METER_PER_KILOMETER": "nm/km",
    "DECIBEL_MILLIWATT": "dBm",
    "DECIBEL": "dB",
    "OHM": "Ohm",
    "LUX": "lx",
}

SUPPORTED_FIELD_CASES = {
    FieldCase.DEFAULT,
    FieldCase.NON_NULL,
    FieldCase.LIST,
    FieldCase.LIST_NON_NULL,
    FieldCase.NON_NULL_LIST,
    FieldCase.NON_NULL_LIST_NON_NULL,
}

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

# TODO: Replace the mapping with the classes of graphql-core and the actual datatypes from the VSS tools.
# SCALAR_DATATYPE_MAP = {
# # Built-in scalar types
# GraphQLInt: Datatypes.INT32[0],
# GraphQLFloat: Datatypes.FLOAT[0],
# GraphQLString: Datatypes.STRING[0],
# GraphQLBoolean: Datatypes.BOOLEAN[0],
# GraphQLID: Datatypes.STRING[0],
# # TODO: Add custom scalar types
# ?: Datatypes.INT8[0],
# ?: Datatypes.UINT8[0],
# ?: Datatypes.INT16[0],
# ?: Datatypes.UINT16[0],
# ?: Datatypes.UINT32[0],
# ?: Datatypes.INT64[0],
# ?: Datatypes.UINT64[0],
# }


class CustomDumper(yaml.Dumper):
    """Custom YAML dumper to add extra line breaks at the top level."""

    def write_line_break(self, data: str | None = None) -> None:
        super().write_line_break(data)
        if len(self.indents) == 1:  # Only add extra line break at the top level
            super().write_line_break()

    def represent_list(self, data: Iterable[Any]) -> yaml.SequenceNode:
        # Check if the list is an inner list (nested list)
        if all(isinstance(item, str) for item in data):
            # Serialize inner lists in flow style
            return super().represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)
        else:
            # Serialize outer lists in block style
            return super().represent_sequence("tag:yaml.org,2002:seq", data, flow_style=False)


# Register the custom representer for lists
CustomDumper.add_representer(list, CustomDumper.represent_list)


def translate_to_vspec(schema_path: Path, naming_config: dict[str, Any] | None = None) -> str:
    """Translate a GraphQL schema to YAML."""
    schema = load_schema_with_naming(schema_path, naming_config)

    all_object_types = get_all_object_types(schema)
    log.debug(f"Object types: {all_object_types}")
    instance_tag_objects = get_all_objects_with_directive(all_object_types, "instanceTag")
    # Remove instance tag objects from object_types
    object_types = [obj for obj in all_object_types if obj not in instance_tag_objects]
    log.debug(f"Instance Tag Objects: {instance_tag_objects}")
    global INSTANCE_TAGS
    INSTANCE_TAGS = get_all_expanded_instance_tags(schema)
    nested_types: list[tuple[str, str]] = []  # List to collect nested structures to reconstruct the path
    yaml_dict = {}
    for object_type in object_types:
        if object_type.name == "Query":
            log.debug("Skipping Query object type.")
            continue

        # Add a VSS branch structure for the object type
        if object_type.name not in yaml_dict:
            yaml_dict.update(process_object_type(object_type, schema))
        else:
            # TODO: Check if the processed object type is already in the yaml_dict
            log.debug(f"Object type '{object_type.name}' already exists in the YAML dictionary. Skipping.")
        # Process the fields of the object type
        for field_name, field in object_type.fields.items():
            # Add a VSS leaf structure for the field
            field_result = process_field(field_name, field, object_type, schema, nested_types)
            if field_result is not None:
                yaml_dict.update(field_result)
            else:
                log.debug(
                    f"Skipping field '{field_name}' in object type '{object_type.name}' as process_field returned None."
                )

    log.debug(f"Nested types: {nested_types}")
    reconstructed_paths = reconstruct_paths(nested_types)
    log.debug(f"Reconstructed {reconstructed_paths}")
    # TODO: Think of splitting the yaml dump into two: one for object types and one for fields.
    # Reason: to maintain the same order of the keys in the fields, and also to structure the
    # export better and sorted for easier control of the output.
    for key in list(yaml_dict.keys()):
        first_word = key.split(".")[0]
        for path in reconstructed_paths:
            path_parts = path.split(".")
            if first_word == path_parts[-1]:
                new_key = ".".join(path_parts[:-1] + [key])
                yaml_dict[new_key] = yaml_dict.pop(key)
                break
    return yaml.dump(yaml_dict, default_flow_style=False, Dumper=CustomDumper, sort_keys=True)


def process_object_type(object_type: GraphQLObjectType, schema: GraphQLSchema) -> dict[str, dict[str, Any]]:
    """Process a GraphQL object type and generate the corresponding YAML."""
    log.info(f"Processing object type '{object_type.name}'.")

    obj_dict: dict[str, Any] = {
        "type": "branch",
    }
    if object_type.description:
        obj_dict["description"] = object_type.description

    instance_tag_object = get_instance_tag_object(object_type, schema)
    if instance_tag_object:
        log.debug(f"Object type '{object_type.name}' has instance tag '{instance_tag_object}'.")
        obj_dict["instances"] = list(get_instance_tag_dict(instance_tag_object).values())
    else:
        log.debug(f"Object type '{object_type.name}' does not have an instance tag.")

    return {object_type.name: obj_dict}


def process_field(
    field_name: str,
    field: GraphQLField,
    object_type: GraphQLObjectType,
    schema: GraphQLSchema,
    nested_types: list[tuple[str, str]],
) -> dict[str, dict[str, Any]]:
    """Process a GraphQL field and generate the corresponding YAML."""
    log.info(f"Processing field '{field_name}'.")
    concat_field_name = f"{object_type.name}.{field_name}"

    output_type = get_named_type(field.type)
    if isinstance(output_type, GraphQLScalarType):
        field_dict: dict[str, Any] = {
            "description": field.description if field.description else "",
            "datatype": SCALAR_DATATYPE_MAP[output_type.name],
        }
        # TODO: Fix numbers that are appearing with quotes as strings.
        if has_directive(field, "range") and field.ast_node and field.ast_node.directives:
            range_directive = next(
                (directive for directive in field.ast_node.directives if directive.name.value == "range"), None
            )
            if range_directive:
                min_arg = next(
                    (
                        arg.value.value
                        for arg in range_directive.arguments
                        if arg.name.value == "min" and hasattr(arg.value, "value")
                    ),
                    None,
                )
                max_arg = next(
                    (
                        arg.value.value
                        for arg in range_directive.arguments
                        if arg.name.value == "max" and hasattr(arg.value, "value")
                    ),
                    None,
                )
                if min_arg is not None:
                    field_dict["min"] = int(min_arg)
                if max_arg is not None:
                    field_dict["max"] = int(max_arg)

        # TODO: Map the unit name. i.e., SCREAMMING_SNAKE_CASE used in graphql to abbreviated vss unit name.
        if "unit" in field.args:
            unit_arg = field.args["unit"].default_value
            if unit_arg is not None:
                field_dict["unit"] = UNITS_DICT[unit_arg]

        if has_directive(field, "metadata"):
            metadata_directive = None
            if field.ast_node and field.ast_node.directives:
                metadata_directive = next(
                    (directive for directive in field.ast_node.directives if directive.name.value == "metadata"), None
                )

            metadata_args = {}
            if metadata_directive and metadata_directive.arguments:
                for arg in metadata_directive.arguments:
                    if hasattr(arg.value, "value"):  # Ensure arg.value has the 'value' attribute
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
        # nested_types.append(f"{object_type.name}.{output_type}({field_name})")
        nested_types.append((object_type.name, output_type.name))
        log.debug(f"Nested structure found: {object_type.name}.{output_type}(for field {field_name})")
        named_type = get_named_type(field.type)
        if isinstance(named_type, GraphQLObjectType):
            return process_object_type(named_type, schema)  # Nested object type, process it recursively
        else:
            log.debug(f"Skipping nested type '{named_type}' as it is not a GraphQLObjectType.")
            return {}
    elif isinstance(output_type, GraphQLEnumType):
        field_dict = {
            "description": field.description if field.description else "",
            "datatype": "string",  # TODO: Consider that VSS allows any datatype for enums.
            "allowed": [value.value for value in field.type.values.values()]
            if isinstance(field.type, GraphQLEnumType)
            else [],
            "type": "attribute",  # TODO: Get this from the @metadata directive.
        }
        return {concat_field_name: field_dict}

    else:
        log.debug(f"Skipping in the output: field '{field_name}' with output type '{type(field.type).__name__}'.")
        return {}


def reconstruct_paths(nested_types: list[tuple[str, str]]) -> list[str]:
    # Dictionary to store the graph structure
    graph: dict[str, list[str]] = {}
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
    def build_paths(current: str, path: list[str]) -> None:
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
) -> None:
    result = translate_to_vspec(schema)
    log.info(f"Result:\n{result}")
    with open(output, "w", encoding="utf-8") as output_file:
        log.info(f"Writing data to '{output}'")
        output_file.write(result)


if __name__ == "__main__":
    main()
