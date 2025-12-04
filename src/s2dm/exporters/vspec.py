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
    Undefined,
    get_named_type,
)

from s2dm import log
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema
from s2dm.exporters.utils.directive import get_directive_arguments, has_given_directive
from s2dm.exporters.utils.extraction import get_all_object_types
from s2dm.exporters.utils.field import FieldCase
from s2dm.exporters.utils.graphql_type import is_introspection_or_root_type
from s2dm.exporters.utils.schema_loader import load_schema_with_naming, process_schema

UNITS_DICT = {  # TODO: move to a separate file or use the vss tools to get the mapping directly from dynamic_units
    # Using the QUDT unit names
    # LengthUnitEnum
    "MILLIM": "mm",
    "CENTIM": "cm",
    "M": "m",
    "METER": "m",
    "KILOM": "km",
    "IN": "inch",
    # VelocityUnitEnum
    "KILOM_PER_HR": "km/h",
    "M_PER_SEC": "m/s",
    # AccelerationUnitEnum
    "M_PER_SEC2": "m/s^2",
    "CENTIM_PER_SEC2": "cm/s^2",
    # VolumeUnitEnum
    "MILLIL": "ml",
    "L": "l",  # Liter
    "CENTIM3": "cm^3",
    # TemperatureUnitEnum
    "DEG_C": "celsius",
    # AngleUnitEnum
    "DEG": "degrees",
    # AngularVelocityUnitEnum
    "DEG_PER_SEC": "degrees/s",
    "RAD_PER_SEC": "rad/s",
    # PowerUnitEnum
    "HP": "PS",  # Horsepower
    # ElectricPowerUnitEnum
    "W": "W",  # Watt
    "KILOW": "kW",  # Kilowatt
    # MassUnitEnum
    "GM": "g",  # Gram
    "KILOGM": "kg",  # Kilogram
    "LB": "lbs",  # Pound
    # ElectricPotentialUnitEnum
    "V": "V",  # Volt
    # DisplacementCurrentUnitEnum
    "AMPERE": "A",
    # ElectricChargeUnitEnum
    "A_HR": "Ah",  # Ampere Hour
    # TimeUnitEnum
    "MILLISEC": "ms",  # Millisecond
    "SEC": "s",  # Second
    "MIN": "min",  # Minute
    "HR": "h",  # Hour
    "DAY": "day",  # Day
    "WK": "weeks",  # Week
    "MO": "months",  # Month
    "YR": "years",  # Year
    # ForcePerAreaUnitEnum
    "MILLIBAR": "mbar",
    "PA": "Pa",  # Pascal
    "KILOPA": "kPa",  # Kilopascal
    "PSI": "psi",  # Pound per square inch
    # MassFlowRateUnitEnum
    "GRAMS_PER_SECOND": "g/s",
    # MassPerLengthUnitEnum
    "GM_PER_KILOM": "g/km",
    # VolumeFlowRateUnitEnum
    "L_PER_HR": "l/h",
    # ForceUnitEnum
    "N": "N",  # Newton
    "KILON": "kN",
    # TorqueUnitEnum
    "N_M": "Nm",  # Newton meter
    # RotationalVelocityUnitEnum
    "REV_PER_MIN": "rpm",
    "HZ": "Hz",  # Hertz
    # HeartRateUnitEnum
    "BEAT_PER_MIN": "bpm",
    # DimensionlessRatioUnitEnum
    "PERCENT": "percent",
    # UnknownUnitEnum
    "DECIB_MILLIW": "dBm",
    # SoundPowerLevelUnitEnum
    "DECIB": "dB",
    # ResistanceUnitEnum
    "OHM": "Ohm",
    # LuminousFluxPerAreaUnitEnum
    "LUX": "lx",
    # Custom units
    "KILOWATT_HOURS": "kWh",
    "UNIX_TIMESTAMP": "unix-time",
    "ISO_8601": "iso8601",
    "STARS": "stars",
    "KILOWATT_HOURS_PER_100_KILOMETERS": "kWh/100km",
    "WATT_HOUR_PER_KM": "Wh/km",
    "MILLILITER_PER_100_KILOMETERS": "ml/100km",
    "LITER_PER_100_KILOMETERS": "l/100km",
    "MILES_PER_GALLON": "mpg",
    "KILOMETERS_PER_LITER": "km/l",
    "CYCLES_PER_MINUTE": "cpm",
    "RATIO": "ratio",
    "NANO_METER_PER_KILOMETER": "nm/km",
}

SUPPORTED_FIELD_CASES = {
    FieldCase.DEFAULT,
    FieldCase.NON_NULL,
    FieldCase.LIST,
    FieldCase.LIST_NON_NULL,
    FieldCase.NON_NULL_LIST,
    FieldCase.NON_NULL_LIST_NON_NULL,
}

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


def translate_to_vspec(annotated_schema: AnnotatedSchema) -> str:
    """Translate a GraphQL schema to YAML."""
    schema = annotated_schema.schema

    all_object_types = get_all_object_types(schema)
    log.debug(f"Object types: {all_object_types}")
    nested_types: list[tuple[str, str]] = []  # List to collect nested structures to reconstruct the path
    yaml_dict = {}
    for object_type in all_object_types:
        if is_introspection_or_root_type(object_type.name):
            log.debug(f"Skipping internal object type '{object_type.name}'.")
            continue

        type_metadata = annotated_schema.type_metadata.get(object_type.name)
        if type_metadata and type_metadata.is_intermediate_type:
            log.debug(f"Skipping intermediate type '{object_type.name}'.")
            continue

        # Add a VSS branch structure for the object type
        if object_type.name not in yaml_dict:
            log.debug(f"Processing object type '{object_type.name}'.")
            obj_dict: dict[str, Any] = {"type": "branch"}
            if object_type.description:
                obj_dict["description"] = object_type.description
            yaml_dict[object_type.name] = obj_dict
        else:
            log.debug(f"Object type '{object_type.name}' already exists in the YAML dictionary. Skipping.")
        # Process the fields of the object type
        for field_name, field in object_type.fields.items():
            # Add a VSS leaf structure for the field
            field_result = process_field(field_name, field, object_type, schema, nested_types, annotated_schema)
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


def process_field(
    field_name: str,
    field: GraphQLField,
    object_type: GraphQLObjectType,
    schema: GraphQLSchema,
    nested_types: list[tuple[str, str]],
    annotated_schema: AnnotatedSchema,
) -> dict[str, dict[str, Any]]:
    """Process a GraphQL field and generate the corresponding YAML."""
    log.debug(f"Processing field '{field_name}'.")
    concat_field_name = f"{object_type.name}.{field_name}"

    output_type = get_named_type(field.type)
    if isinstance(output_type, GraphQLScalarType):
        field_dict: dict[str, Any] = {
            "description": field.description if field.description else "",
            "datatype": SCALAR_DATATYPE_MAP[output_type.name],
        }

        # TODO: Fix numbers that are appearing with quotes as strings.
        if has_given_directive(field, "range"):
            args = get_directive_arguments(field, "range")
            datatype = field_dict["datatype"]
            is_integer_type = "int" in datatype
            is_float_type = datatype in ("float", "double")

            if "min" in args:
                if is_integer_type:
                    field_dict["min"] = int(args["min"])
                elif is_float_type:
                    field_dict["min"] = float(args["min"])
                else:
                    field_dict["min"] = args["min"]
            if "max" in args:
                if is_integer_type:
                    field_dict["max"] = int(args["max"])
                elif is_float_type:
                    field_dict["max"] = float(args["max"])
                else:
                    field_dict["max"] = args["max"]

        # TODO: Map the unit name. i.e., SCREAMMING_SNAKE_CASE used in graphql to abbreviated vss unit name.
        if "unit" in field.args:
            unit_arg = field.args["unit"].default_value
            if unit_arg is not None and unit_arg is not Undefined and unit_arg in UNITS_DICT:
                field_dict["unit"] = UNITS_DICT[unit_arg]

        if has_given_directive(field, "metadata"):
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
    elif isinstance(output_type, GraphQLObjectType):
        # Get field_metadata to access resolved_type and instances
        field_meta = annotated_schema.field_metadata.get((object_type.name, field_name))
        if not field_meta:
            log.debug(f"No field_metadata found for '{object_type.name}.{field_name}'.")
            return {}

        # Use resolved_type (skips intermediate types automatically)
        resolved_type_name = field_meta.resolved_type
        resolved_type_obj = schema.type_map.get(resolved_type_name)

        if not isinstance(resolved_type_obj, GraphQLObjectType):
            log.debug(f"Resolved type '{resolved_type_name}' is not a GraphQLObjectType.")
            return {}

        # Record nested relationship using resolved type
        nested_types.append((object_type.name, resolved_type_name))
        log.debug(f"Nested structure found: {object_type.name}.{resolved_type_name} (for field {field_name})")

        # Get instances from field_metadata
        instances = field_meta.instances if field_meta.instances else None

        # Create branch dict inline
        obj_dict: dict[str, Any] = {"type": "branch"}
        if resolved_type_obj.description:
            obj_dict["description"] = resolved_type_obj.description
        if instances:
            obj_dict["instances"] = instances

        return {resolved_type_name: obj_dict}
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
@click.argument("schema", type=click.Path(exists=True, path_type=Path), required=True)
@click.argument("output", type=click.Path(dir_okay=False, writable=True, path_type=Path), required=True)
def main(
    schemas: list[Path],
    output: Path,
) -> None:
    # TODO: deprecate
    graphql_schema = load_schema_with_naming(schemas, None)
    annotated_schema = process_schema(graphql_schema, {}, None, None, None, False)
    result = translate_to_vspec(annotated_schema)
    log.info(f"Result:\n{result}")
    with open(output, "w", encoding="utf-8") as output_file:
        log.info(f"Writing data to '{output}'")
        output_file.write(result)


if __name__ == "__main__":
    main()
