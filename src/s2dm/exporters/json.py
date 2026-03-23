"""JSON Tree Exporter for S2DM.

This exporter generates hierarchical JSON tree structures from a GraphQL schema.

Schema-intrinsic information is extracted directly from the GraphQL schema:
  - description, datatype, min/max (from @range), unit (raw field arg), deprecated

Optional VSS meta overlay (activated by passing a YAML file via `vspec_lookup_path`):
  When a YAML lookup is provided, @vspec annotations are also processed:
  - type from @vspec(element:...), output key renaming via @vspec(fqn:...)
  - allowed values from enum fields annotated with @vspec
  - all YAML entry keys are merged into the leaf node (unit, comment, default, etc.)

Output structure example:

{
  "Vehicle": {
    "children": {
      "Speed": {
        "datatype": "float",
        "description": "Vehicle speed",
        "unit": "km/h",
        "min": 0,
        "max": 250
      },
      ...
    },
    "description": ...
  }
}
"""

import json
from pathlib import Path
from typing import Any, cast

import yaml
from graphql import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    Undefined,
    get_named_type,
    is_enum_type,
    is_list_type,
    is_non_null_type,
    is_object_type,
    is_scalar_type,
)

from s2dm import log
from s2dm.exporters.utils.annotated_schema import AnnotatedSchema
from s2dm.exporters.utils.directive import get_directive_arguments, has_given_directive
from s2dm.exporters.utils.extraction import get_all_object_types
from s2dm.exporters.utils.graphql_type import is_introspection_type


def load_vspec_lookup(path: Path) -> dict[str, Any]:
    """Load a YAML file containing FQN-indexed VSS metadata for overlay.

    Args:
        path: Path to the YAML file with FQN dot-path keys and metadata dicts as values.

    Returns:
        Dictionary mapping FQN strings to metadata dicts.
    """
    return yaml.safe_load(path.read_text()) or {}


class JsonExporter:
    """Exports GraphQL schema to JSON tree structure."""

    def __init__(
        self,
        schema: GraphQLSchema,
        annotated_schema: AnnotatedSchema,
        expanded_instances: bool = False,
        vspec_lookup: dict[str, Any] | None = None,
    ):
        """Initialize JSON exporter.

        Args:
            schema: The GraphQL schema to export
            annotated_schema: Annotated schema with field metadata
            expanded_instances: Whether instance tags have been expanded
            vspec_lookup: Optional dict from load_vspec_lookup() for FQN-indexed overlay
        """
        self.schema = schema
        self.annotated_schema = annotated_schema
        self.expanded_instances = expanded_instances
        self.vspec_lookup = vspec_lookup
        # Flat lookup: merges top-level FQN entries AND ComplexDataTypes sub-entries so that
        # _apply_vspec_lookup can resolve any FQN regardless of where it lives in the YAML.
        self._flat_lookup: dict[str, Any] = {}
        if vspec_lookup is not None:
            for _key, _val in vspec_lookup.items():
                if _key == "ComplexDataTypes" and isinstance(_val, dict):
                    self._flat_lookup.update(_val)
                elif isinstance(_val, dict):
                    self._flat_lookup[_key] = _val

    def export(self, root_type: str | None = None) -> dict[str, Any]:
        """Export schema to JSON tree structure.

        Args:
            root_type: Optional root type name to export. If None, exports all top-level types.

        Returns:
            Dictionary with type names as keys and tree structures as values
        """
        if root_type:
            # Single root export
            if root_type not in self.schema.type_map:
                raise ValueError(f"Root type '{root_type}' not found in schema")

            gql_type = self.schema.type_map[root_type]
            if not is_object_type(gql_type):
                raise ValueError(f"Root type '{root_type}' is not an object type")

            visited: set[str] = set()
            return {root_type: self._build_branch_node(cast(GraphQLObjectType, gql_type), visited)}
        else:
            # Multi-root export - all non-introspection, non-operation object types
            operation_type_names = {
                t.name
                for t in [self.schema.query_type, self.schema.mutation_type, self.schema.subscription_type]
                if t is not None
            }
            user_types = [
                t
                for t in get_all_object_types(self.schema)
                if not is_introspection_type(t.name)
                and t.name not in operation_type_names
                # In vspec-meta mode: STRUCT types are emitted via the ComplexDataTypes section
                and not (self.vspec_lookup is not None and self._is_vspec_struct_type(t))
            ]
            result: dict[str, Any] = {}
            for obj_type in user_types:
                visited = set()
                result[obj_type.name] = self._build_branch_node(obj_type, visited)
            # In vspec-meta mode: build ComplexDataTypes section from YAML if present
            if self.vspec_lookup is not None and "ComplexDataTypes" in self.vspec_lookup:
                complex_entries = self.vspec_lookup["ComplexDataTypes"]
                if isinstance(complex_entries, dict):
                    result["ComplexDataTypes"] = self._build_fqn_tree(complex_entries)
            return result

    def _build_branch_node(self, gql_type: GraphQLObjectType, visited: set[str]) -> dict[str, Any]:
        """Build a branch node (ObjectType) with children.

        Args:
            gql_type: The GraphQL ObjectType to process
            visited: Set of visited type names for cycle detection

        Returns:
            Dictionary representing a branch node with children
        """
        # Check for cycles
        if gql_type.name in visited:
            log.warning(f"Cycle detected for type '{gql_type.name}', using $ref")
            return {"$ref": gql_type.name}

        visited.add(gql_type.name)

        # Build base branch node
        node: dict[str, Any] = {"children": {}}
        # In vspec-meta mode, derive "type" from the type's own @vspec(element:...) if present,
        # falling back to "branch".
        if self.vspec_lookup is not None:
            if has_given_directive(gql_type, "vspec"):
                type_vspec_args = get_directive_arguments(gql_type, "vspec")
                element = type_vspec_args.get("element")
                node["type"] = str(element).lower() if element else "branch"
            else:
                node["type"] = "branch"

        # Add description if present
        if gql_type.description:
            node["description"] = gql_type.description

        # Check for @metadata directive on the type itself
        if has_given_directive(gql_type, "metadata"):
            metadata_args = get_directive_arguments(gql_type, "metadata")
            if "comment" in metadata_args:
                node["comment"] = metadata_args["comment"]

        # Process all fields
        for field_name, field in gql_type.fields.items():
            # Handle @instanceTag fields — they encode instance structure, not data children
            field_named_type = get_named_type(field.type)
            if is_object_type(field_named_type) and has_given_directive(
                cast(GraphQLObjectType, field_named_type), "instanceTag"
            ):
                # In default mode: derive instances from enum dimensions inside the tag
                if self.vspec_lookup is None:
                    dimensions = self._extract_instances_from_instance_tag(cast(GraphQLObjectType, field_named_type))
                    if dimensions:
                        node["instances"] = dimensions
                continue

            # Resolve output key and FQN from @vspec(fqn:...) — only in vspec-meta mode
            output_key = field_name
            fqn: str | None = None
            if self.vspec_lookup is not None and has_given_directive(field, "vspec"):
                vspec_args = get_directive_arguments(field, "vspec")
                raw_fqn = vspec_args.get("fqn")
                if raw_fqn and isinstance(raw_fqn, str):
                    fqn = raw_fqn
                    if "." in fqn:
                        output_key = fqn.rsplit(".", 1)[-1]
            child_node = self._process_field_to_node(field_name, field, gql_type, visited.copy(), fqn=fqn)
            node["children"][output_key] = child_node

        return node

    def _build_struct_field_leaf_node(
        self,
        field: GraphQLField,
        struct_type: GraphQLObjectType,
    ) -> dict[str, Any]:
        """Build a leaf node for a field whose underlying type is a @vspec STRUCT.

        In VSS, a sensor/property with a struct datatype is a leaf — the struct
        definition lives separately in the types tree, and the signal only carries
        the FQN of the struct as its datatype.

        Args:
            field: The GraphQL field referencing the struct type.
            struct_type: The @vspec(element: STRUCT) ObjectType being referenced.

        Returns:
            Leaf node dict with description, datatype (struct FQN), optional
            min/max/unit/deprecated, and type from the field's @vspec element.
        """
        node: dict[str, Any] = {}

        if field.description:
            node["description"] = field.description.strip()

        # Detect list wrapper (NonNull → List)
        ft = field.type
        if is_non_null_type(ft):
            ft = cast("GraphQLNonNull[Any]", ft).of_type
        is_list = is_list_type(ft)

        # datatype = FQN of the struct type from @vspec(fqn:...) on the struct
        struct_vspec_args = get_directive_arguments(struct_type, "vspec")
        struct_fqn = struct_vspec_args.get("fqn")
        if struct_fqn and isinstance(struct_fqn, str):
            node["datatype"] = struct_fqn + ("[]" if is_list else "")

        # @range from this field
        if has_given_directive(field, "range"):
            range_args = get_directive_arguments(field, "range")
            if "min" in range_args and range_args["min"] is not None:
                node["min"] = range_args["min"]
            if "max" in range_args and range_args["max"] is not None:
                node["max"] = range_args["max"]

        # unit from field argument
        if "unit" in field.args:
            unit_arg = field.args["unit"]
            if unit_arg.default_value is not None and unit_arg.default_value is not Undefined:
                node["unit"] = str(unit_arg.default_value)

        # deprecated
        if field.deprecation_reason:
            node["deprecated"] = field.deprecation_reason

        # type from the field's own @vspec(element:...) (sensor, struct_property, etc.)
        if has_given_directive(field, "vspec"):
            vspec_args = get_directive_arguments(field, "vspec")
            element = vspec_args.get("element")
            if element:
                node["type"] = str(element).lower()

        return node

    def _is_vspec_struct_type(self, obj_type: GraphQLObjectType) -> bool:
        """Return True if this type carries @vspec(element: STRUCT)."""
        if not has_given_directive(obj_type, "vspec"):
            return False
        return str(get_directive_arguments(obj_type, "vspec").get("element", "")).upper() == "STRUCT"

    def _build_fqn_tree(self, fqn_entries: dict[str, Any]) -> dict[str, Any]:
        """Build a nested tree from a flat dict of FQN-keyed metadata entries.

        Used to produce the ComplexDataTypes output section entirely from YAML data
        without consulting the GraphQL schema.

        Args:
            fqn_entries: Flat dict keyed by dot-separated FQN strings; values are
                         metadata dicts (type, datatype, description, min, max, …).

        Returns:
            Nested dict representing the hierarchy implied by the FQN paths.
        """
        nodes: dict[str, dict[str, Any]] = {}

        for fqn in sorted(fqn_entries.keys(), key=lambda k: k.count(".")):
            metadata = fqn_entries[fqn]
            node: dict[str, Any] = {k: v for k, v in metadata.items() if v is not None}

            # Add children dict when any direct child exists in the entries
            prefix = fqn + "."
            if any(k.startswith(prefix) and k.count(".") == fqn.count(".") + 1 for k in fqn_entries):
                node["children"] = {}

            nodes[fqn] = node

            # Attach to parent
            parts = fqn.split(".")
            if len(parts) > 1:
                parent_fqn = ".".join(parts[:-1])
                if parent_fqn in nodes:
                    parent_node = nodes[parent_fqn]
                    if "children" not in parent_node:
                        parent_node["children"] = {}
                    parent_node["children"][parts[-1]] = node

        # Return only root-level nodes (FQNs with no dots)
        return {fqn: nodes[fqn] for fqn in nodes if "." not in fqn}

    def _extract_instances_from_instance_tag(self, instance_tag_type: GraphQLObjectType) -> list[list[str]]:
        """Extract instance dimensions from an @instanceTag type's enum fields.

        Each enum-typed field in the instanceTag type represents one dimension;
        its values (in definition order) form the list for that dimension.

        Args:
            instance_tag_type: The GraphQL ObjectType carrying the @instanceTag directive.

        Returns:
            List of dimensions, each a list of enum value name strings.
        """
        dimensions: list[list[str]] = []
        for _, field in instance_tag_type.fields.items():
            field_type = get_named_type(field.type)
            if is_enum_type(field_type):
                enum_type = cast(GraphQLEnumType, field_type)
                dimensions.append(list(enum_type.values.keys()))
        return dimensions

    def _apply_vspec_lookup(self, node: dict[str, Any], fqn: str) -> None:
        """Overlay node properties from the vspec_lookup YAML using the given FQN.

        Merges all keys from the YAML entry into `node`, overwriting existing values.
        Supported keys: type, datatype, description, unit, min, max, allowed, comment,
        default, deprecated.

        Args:
            node: The leaf node dict to update in-place.
            fqn: The fully-qualified name to look up in self.vspec_lookup.
        """
        if self.vspec_lookup is None:
            return
        entry = self._flat_lookup.get(fqn)
        if not entry or not isinstance(entry, dict):
            return
        for key, value in entry.items():
            if value is not None:
                node[key] = value

    def _process_field_to_node(
        self,
        field_name: str,
        field: GraphQLField,
        parent_type: GraphQLObjectType,
        visited: set[str],
        fqn: str | None = None,
    ) -> dict[str, Any]:
        """Process a GraphQL field and return its node representation.

        Args:
            field_name: The name of the field
            field: The GraphQL field to process
            parent_type: The parent ObjectType containing this field
            visited: Set of visited type names for cycle detection
            fqn: Optional fully-qualified name from @vspec for vspec_lookup overlay

        Returns:
            Node dictionary
        """
        field_type = get_named_type(field.type)

        # Check if field is an ObjectType (branch node)
        if is_object_type(field_type):
            obj_type = cast(GraphQLObjectType, field_type)

            # Skip @instanceTag types — guarded upstream, but kept as safety net
            if has_given_directive(obj_type, "instanceTag"):
                log.warning(f"Skipping @instanceTag type '{obj_type.name}' as field")
                return {"children": {}}

            # In vspec-meta mode: fields referencing a @vspec(element: STRUCT) type are leaf
            # nodes whose datatype is the struct's FQN, not expanded branch nodes.
            if self.vspec_lookup is not None and has_given_directive(obj_type, "vspec"):
                struct_vspec = get_directive_arguments(obj_type, "vspec")
                if str(struct_vspec.get("element", "")).upper() == "STRUCT":
                    leaf_node = self._build_struct_field_leaf_node(field, obj_type)
                    if fqn:
                        self._apply_vspec_lookup(leaf_node, fqn)
                    return leaf_node

            # Build branch node recursively
            branch_node = self._build_branch_node(obj_type, visited)

            # Add description from field's docstring
            if field.description:
                branch_node["description"] = field.description.strip()

            # Check for instances metadata (from annotated schema — default mode)
            field_meta = self.annotated_schema.field_metadata.get((parent_type.name, field_name))
            if field_meta and field_meta.instances:
                branch_node["instances"] = field_meta.instances

            # Apply YAML overlay for branch node (sets instances, type, comment, etc.)
            if fqn and self.vspec_lookup is not None:
                self._apply_vspec_lookup(branch_node, fqn)

            return branch_node

        # Leaf node (scalar or enum)
        leaf_node = self._extract_leaf_properties(field)

        # Apply YAML overlay if a vspec_lookup is configured
        if fqn and self.vspec_lookup is not None:
            self._apply_vspec_lookup(leaf_node, fqn)

        return leaf_node

    def _extract_leaf_properties(self, field: GraphQLField) -> dict[str, Any]:
        """Extract properties from a leaf field (scalar or enum).

        Default mode (no vspec_lookup): extracts only schema-intrinsic fields:
          description, datatype, min/max (from @range), unit (from field arg), deprecated.

        Vspec-meta mode (vspec_lookup is set): also processes @vspec to add
          type (from element) and allowed (for enum fields). The YAML overlay is
          applied afterwards in _process_field_to_node.

        Args:
            field: The GraphQL field to extract properties from

        Returns:
            Dictionary with leaf node properties
        """
        node: dict[str, Any] = {}

        # Get the actual field type (unwrap NonNull/List wrappers)
        field_type = field.type
        is_non_null = is_non_null_type(field_type)
        is_list = False

        if is_non_null:
            field_type = cast("GraphQLNonNull[Any]", field_type).of_type

        if is_list_type(field_type):
            is_list = True
            field_type = cast("GraphQLList[Any]", field_type).of_type
            # Unwrap NonNull inside list if present
            if is_non_null_type(field_type):
                field_type = cast("GraphQLNonNull[Any]", field_type).of_type

        named_type = get_named_type(field_type)

        # Add description (always included if present)
        if field.description:
            node["description"] = field.description

        # Determine datatype (always included)
        if is_scalar_type(named_type):
            scalar = cast(GraphQLScalarType, named_type)
            datatype = scalar.name
            if is_list:
                datatype += "[]"
            node["datatype"] = datatype
        elif is_enum_type(named_type):
            datatype = named_type.name
            if is_list:
                datatype += "[]"
            node["datatype"] = datatype

        # Extract from @range directive
        if has_given_directive(field, "range"):
            range_args = get_directive_arguments(field, "range")
            if "min" in range_args and range_args["min"] is not None:
                node["min"] = range_args["min"]
            if "max" in range_args and range_args["max"] is not None:
                node["max"] = range_args["max"]

        # Extract unit from field arguments.
        if "unit" in field.args:
            unit_arg = field.args["unit"]
            if unit_arg.default_value is not None and unit_arg.default_value is not Undefined:
                node["unit"] = str(unit_arg.default_value)

        # Add deprecated if present
        if field.deprecation_reason:
            node["deprecated"] = field.deprecation_reason

        # Handle @vspec directive — only in vspec-meta mode (vspec_lookup is configured)
        if self.vspec_lookup is not None and has_given_directive(field, "vspec"):
            vspec_args = get_directive_arguments(field, "vspec")

            # Extract element type (maps to "type" in output)
            if "element" in vspec_args and vspec_args["element"]:
                # Convert from VSPEC element enum to lowercase string
                element = str(vspec_args["element"]).lower()
                node["type"] = element

            # For enum types with @vspec, add allowed values
            if is_enum_type(named_type):
                enum_type = cast(GraphQLEnumType, named_type)
                node["allowed"] = list(enum_type.values.keys())

        return node


def export_to_json_tree(
    annotated_schema: AnnotatedSchema,
    root_type: str | None = None,
    output_file: Path | None = None,
    vspec_lookup_path: Path | None = None,
) -> dict[str, Any]:
    """Export GraphQL schema to JSON tree format.

    Args:
        annotated_schema: The annotated schema to export
        root_type: Optional root type name. If None, exports all top-level types.
        output_file: Optional output file path. If provided, writes JSON to file.
        vspec_lookup_path: Optional path to a YAML file with FQN-indexed metadata overlay.
            When provided, leaf node properties are overwritten by matching YAML entries.

    Returns:
        Dictionary representing the JSON tree
    """
    vspec_lookup: dict[str, Any] | None = None
    if vspec_lookup_path is not None:
        vspec_lookup = load_vspec_lookup(vspec_lookup_path)

    exporter = JsonExporter(
        annotated_schema.schema,
        annotated_schema,
        expanded_instances=False,  # Determined by schema loading
        vspec_lookup=vspec_lookup,
    )

    result = exporter.export(root_type=root_type)

    if output_file:
        output_file.write_text(json.dumps(result, indent=2))
        log.info(f"Exported JSON tree to {output_file}")

    return result
