from typing import Any, cast

from graphql import (
    GraphQLEnumType,
    GraphQLField,
    GraphQLInterfaceType,
    GraphQLList,
    GraphQLNonNull,
    GraphQLObjectType,
    GraphQLScalarType,
    GraphQLSchema,
    GraphQLType,
    GraphQLUnionType,
    is_enum_type,
    is_interface_type,
    is_list_type,
    is_non_null_type,
    is_object_type,
    is_scalar_type,
    is_union_type,
)

from s2dm import log
from s2dm.exporters.utils.directive import get_directive_arguments, has_given_directive
from s2dm.exporters.utils.extraction import get_all_named_types
from s2dm.exporters.utils.field import get_cardinality
from s2dm.exporters.utils.graphql_type import is_root_type
from s2dm.exporters.utils.instance_tag import (
    is_instance_tag_field,
    is_valid_instance_tag_field,
)

# MongoDB supports draft 4 of JSON Schema with BSON type extensions.
# Unsupported keywords: $ref, $schema, definitions, default, format, id, integer type.
# Use bsonType instead of type; use int/long instead of integer.

# ---------------------------------------------------------------------------
# GeoJSON BSON schemas (RFC 7946 — https://www.rfc-editor.org/rfc/rfc7946)
# Used when a field is typed as the GeoJSON scalar with @geoType directive.
# Note: MongoDB $jsonSchema enforces the first level precisely; deeper nesting
# is expressed best-effort since oneOf/anyOf are not supported.
# ---------------------------------------------------------------------------

_GEOJSON_POINT_SCHEMA: dict[str, Any] = {
    "bsonType": "object",
    "required": ["type", "coordinates"],
    "properties": {
        "type": {"bsonType": "string", "enum": ["Point"]},
        "coordinates": {
            "bsonType": "array",
            "items": {"bsonType": "double"},
            "minItems": 2,
            "maxItems": 2,
        },
    },
}

_GEOJSON_MULTIPOINT_SCHEMA: dict[str, Any] = {
    "bsonType": "object",
    "required": ["type", "coordinates"],
    "properties": {
        "type": {"bsonType": "string", "enum": ["MultiPoint"]},
        "coordinates": {
            "bsonType": "array",
            "items": {
                "bsonType": "array",
                "items": {"bsonType": "double"},
                "minItems": 2,
            },
        },
    },
}

_GEOJSON_LINESTRING_SCHEMA: dict[str, Any] = {
    "bsonType": "object",
    "required": ["type", "coordinates"],
    "properties": {
        "type": {"bsonType": "string", "enum": ["LineString"]},
        "coordinates": {
            "bsonType": "array",
            "items": {
                "bsonType": "array",
                "items": {"bsonType": "double"},
                "minItems": 2,
            },
            "minItems": 2,
        },
    },
}

_GEOJSON_MULTILINESTRING_SCHEMA: dict[str, Any] = {
    "bsonType": "object",
    "required": ["type", "coordinates"],
    "properties": {
        "type": {"bsonType": "string", "enum": ["MultiLineString"]},
        "coordinates": {
            "bsonType": "array",
            "items": {
                "bsonType": "array",
                "items": {
                    "bsonType": "array",
                    "items": {"bsonType": "double"},
                    "minItems": 2,
                },
                "minItems": 2,
            },
        },
    },
}

_GEOJSON_POLYGON_SCHEMA: dict[str, Any] = {
    "bsonType": "object",
    "required": ["type", "coordinates"],
    "properties": {
        "type": {"bsonType": "string", "enum": ["Polygon"]},
        "coordinates": {
            "bsonType": "array",
            "items": {
                # Each linear ring: array of positions, first == last, minItems 4
                "bsonType": "array",
                "items": {
                    "bsonType": "array",
                    "items": {"bsonType": "double"},
                    "minItems": 2,
                },
                "minItems": 4,
            },
        },
    },
}

_GEOJSON_MULTIPOLYGON_SCHEMA: dict[str, Any] = {
    "bsonType": "object",
    "required": ["type", "coordinates"],
    "properties": {
        "type": {"bsonType": "string", "enum": ["MultiPolygon"]},
        "coordinates": {
            "bsonType": "array",
            "items": {
                "bsonType": "array",
                "items": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "array",
                        "items": {"bsonType": "double"},
                        "minItems": 2,
                    },
                    "minItems": 4,
                },
            },
        },
    },
}

# Permissive fallback: GeoJSON scalar without @geoType.
# Requires 'type' (string) and 'coordinates' (array) but does not constrain geometry shape.
_GEOJSON_GENERIC_SCHEMA: dict[str, Any] = {
    "bsonType": "object",
    "required": ["type", "coordinates"],
    "properties": {
        "type": {"bsonType": "string"},
        "coordinates": {"bsonType": "array"},
    },
}

_GEOJSON_SCHEMAS: dict[str, dict[str, Any]] = {
    "POINT": _GEOJSON_POINT_SCHEMA,
    "MULTIPOINT": _GEOJSON_MULTIPOINT_SCHEMA,
    "LINESTRING": _GEOJSON_LINESTRING_SCHEMA,
    "MULTILINESTRING": _GEOJSON_MULTILINESTRING_SCHEMA,
    "POLYGON": _GEOJSON_POLYGON_SCHEMA,
    "MULTIPOLYGON": _GEOJSON_MULTIPOLYGON_SCHEMA,
}

GRAPHQL_SCALAR_TO_BSON: dict[str, str] = {
    "String": "string",
    "Int": "int",
    "Float": "double",
    "Boolean": "bool",
    "ID": "objectId",
    "Int8": "int",
    "UInt8": "int",
    "Int16": "int",
    "UInt16": "int",
    "UInt32": "int",
    "Int64": "long",
    "UInt64": "long",
}


class MongoDBTransformer:
    """
    Converts a GraphQL schema to per-type MongoDB BSON validator schemas.

    Uses ``bsonType`` (not ``type``). All nested types are inlined — no ``$ref``.
    Enums inlined at usage. Nullable fields: ``bsonType: [<type>, "null"]``.
    Root types and ``@instanceTag`` types are excluded as top-level entries.
    The ``instanceTag`` field on parent types (the reference to the tag structure)
    is also dropped — without ``--expanded-instances`` the tag structure has no
    representation in the output.
    Circular references raise ``ValueError``.

    Parameters
    ----------
    graphql_schema:
        The compiled GraphQL schema to export.
    additional_props_false:
        Set of keys for which ``additionalProperties: false`` should be emitted.
        Each entry is either a bare type name (``"Address"``) or a
        ``Parent.field`` path (``"ChargingStation.address"``).
        When empty (the default) no ``additionalProperties`` key is emitted at all.
    """

    def __init__(
        self,
        graphql_schema: GraphQLSchema,
        additional_props_false: frozenset[str] | None = None,
    ) -> None:
        self.graphql_schema = graphql_schema
        self._additional_props_false: frozenset[str] = additional_props_false or frozenset()

    def transform(self) -> dict[str, dict[str, Any]]:
        """Return ``{type_name: bson_schema}`` for every exportable object/interface/union type."""
        if self._additional_props_false:
            self._validate_properties_config()

        result: dict[str, dict[str, Any]] = {}

        for type_def in get_all_named_types(self.graphql_schema):
            if is_scalar_type(type_def) or is_enum_type(type_def):
                continue  # inlined at usage; no top-level entry

            if is_object_type(type_def):
                obj = cast(GraphQLObjectType, type_def)
                if has_given_directive(obj, "instanceTag"):
                    log.debug(f"Skipping @instanceTag type: {obj.name}")
                    continue
                if is_root_type(type_def.name):
                    log.debug(f"Skipping root type: {type_def.name}")
                    continue
                result[type_def.name] = self._build_object_schema(obj, frozenset(), type_key=type_def.name)

            elif is_interface_type(type_def):
                iface = cast(GraphQLInterfaceType, type_def)
                result[type_def.name] = self._build_interface_schema(iface, frozenset(), type_key=type_def.name)

            elif is_union_type(type_def):
                union = cast(GraphQLUnionType, type_def)
                result[type_def.name] = self._build_union_schema(union, frozenset())

        return result

    def _validate_properties_config(self) -> None:
        """Raise ``ValueError`` listing every entry in the properties config that does not
        correspond to a known object/interface type (or field on one) in the schema.

        Rules:
        - ``"TypeName"`` → ``TypeName`` must be an object or interface type in the schema.
        - ``"TypeName.fieldName"`` → ``TypeName`` must be an object/interface AND must have
          a field named ``fieldName``.
        """
        errors: list[str] = []
        for key in sorted(self._additional_props_false):
            parts = key.split(".")
            type_name = parts[0]
            type_def = self.graphql_schema.type_map.get(type_name)

            if type_def is None:
                errors.append(f"  '{key}': type '{type_name}' does not exist in the schema.")
                continue

            if not (is_object_type(type_def) or is_interface_type(type_def)):
                errors.append(
                    f"  '{key}': '{type_name}' is not an object or interface type " f"(got {type(type_def).__name__})."
                )
                continue

            if len(parts) == 2:
                field_name = parts[1]
                fields = (
                    cast(GraphQLObjectType, type_def).fields
                    if is_object_type(type_def)
                    else cast(GraphQLInterfaceType, type_def).fields
                )
                if field_name not in fields:
                    errors.append(f"  '{key}': type '{type_name}' has no field '{field_name}'.")

        if errors:
            detail = "Invalid properties-config entries:\n" + "\n".join(errors)
            log.error(detail)
            raise ValueError(detail + "\nFix the file passed to '--properties-config' and try again.")

    # ------------------------------------------------------------------
    # Schema builders (return bare dicts, no $jsonSchema wrapper)
    # ------------------------------------------------------------------

    def _build_object_schema(
        self,
        object_type: GraphQLObjectType,
        resolving: frozenset[str],
        type_key: str | None = None,
    ) -> dict[str, Any]:
        if object_type.name in resolving:
            chain = " -> ".join(sorted(resolving))
            raise ValueError(
                f"Circular reference detected: '{chain}' -> '{object_type.name}'. "
                "MongoDB validators do not support $ref; circular types cannot be inlined."
            )
        resolving = resolving | {object_type.name}

        schema: dict[str, Any] = {"bsonType": "object", "properties": {}}
        if object_type.description:
            schema["description"] = object_type.description

        # Emit additionalProperties: false when listed in config, true otherwise.
        # type_key is either the bare type name (top-level) or "Parent.field" (inline).
        schema["additionalProperties"] = not (type_key is not None and type_key in self._additional_props_false)

        required: list[str] = []
        for field_name, field in object_type.fields.items():
            if is_valid_instance_tag_field(field, self.graphql_schema):
                if is_instance_tag_field(field_name):
                    continue
                raise ValueError(f"Invalid schema: @instanceTag object found on non-instanceTag field '{field_name}'")
            if is_non_null_type(field.type):
                required.append(field_name)
            # Compute the inline key for this field: "ParentType.fieldName"
            inline_key = f"{object_type.name}.{field_name}" if type_key is not None else None
            schema["properties"][field_name] = self._build_field_schema(field, resolving, inline_key=inline_key)

        if required:
            schema["required"] = required
        return schema

    def _build_interface_schema(
        self,
        interface_type: GraphQLInterfaceType,
        resolving: frozenset[str],
        type_key: str | None = None,
    ) -> dict[str, Any]:
        if interface_type.name in resolving:
            raise ValueError(f"Circular reference detected involving interface '{interface_type.name}'.")
        resolving = resolving | {interface_type.name}

        schema: dict[str, Any] = {"bsonType": "object", "properties": {}}
        if interface_type.description:
            schema["description"] = interface_type.description

        schema["additionalProperties"] = not (type_key is not None and type_key in self._additional_props_false)

        required: list[str] = []
        for field_name, field in interface_type.fields.items():
            if is_non_null_type(field.type):
                required.append(field_name)
            inline_key = f"{interface_type.name}.{field_name}" if type_key is not None else None
            schema["properties"][field_name] = self._build_field_schema(field, resolving, inline_key=inline_key)

        if required:
            schema["required"] = required
        return schema

    def _build_union_schema(
        self,
        union_type: GraphQLUnionType,
        resolving: frozenset[str],
    ) -> dict[str, Any]:
        members: list[dict[str, Any]] = [self._build_object_schema(member, resolving) for member in union_type.types]
        schema: dict[str, Any] = {"oneOf": members}
        if union_type.description:
            schema["description"] = union_type.description
        return schema

    # ------------------------------------------------------------------
    # Field / type resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _unwrapped_scalar_name(field_type: GraphQLType) -> str | None:
        """Return the scalar name if field_type (unwrapping a single NonNull) is a scalar."""
        unwrapped = cast(GraphQLNonNull[Any], field_type).of_type if is_non_null_type(field_type) else field_type
        return cast(GraphQLScalarType, unwrapped).name if is_scalar_type(unwrapped) else None

    def _build_geojson_schema(self, shape: str, nullable: bool) -> dict[str, Any]:
        """Return the BSON schema for a GeoJSON field, with optional null union."""
        base = dict(_GEOJSON_SCHEMAS.get(shape, _GEOJSON_GENERIC_SCHEMA))
        if nullable:
            base["bsonType"] = [cast(str, base.get("bsonType", "object")), "null"]
        return base

    def _build_field_schema(
        self,
        field: GraphQLField,
        resolving: frozenset[str],
        inline_key: str | None = None,
    ) -> dict[str, Any]:
        # --- GeoJSON scalar with @geoType directive → precise BSON shape ---
        # Must be checked before _get_type_schema because the shape context
        # lives on the field directive, not on the type itself.
        if self._unwrapped_scalar_name(field.type) == "GeoJSON" and has_given_directive(field, "geoType"):
            shape = str(get_directive_arguments(field, "geoType").get("shape", ""))
            nullable = not is_non_null_type(field.type)
            schema = self._build_geojson_schema(shape, nullable)
            if field.description:
                schema["description"] = field.description
            return schema

        schema = self._get_type_schema(field.type, nullable=True, resolving=resolving, inline_key=inline_key)

        if field.description:
            schema["description"] = field.description

        if hasattr(field, "ast_node") and field.ast_node and field.ast_node.directives:
            directive_result = self._process_directives(field, field.type)
            schema.update(directive_result["field"])
            # range on list-item types goes into items
            if directive_result["contained_type"]:
                bson_t = schema.get("bsonType")
                is_array = bson_t == "array" or (isinstance(bson_t, list) and "array" in bson_t)
                if is_array and "items" in schema:
                    schema["items"].update(directive_result["contained_type"])

        return schema

    def _get_type_schema(
        self,
        field_type: GraphQLType,
        nullable: bool,
        resolving: frozenset[str],
        inline_key: str | None = None,
    ) -> dict[str, Any]:
        # --- NonNull wrapper ---
        if is_non_null_type(field_type):
            return self._get_type_schema(
                cast(GraphQLNonNull[Any], field_type).of_type,
                nullable=False,
                resolving=resolving,
                inline_key=inline_key,
            )

        # --- List ---
        if is_list_type(field_type):
            list_type = cast(GraphQLList[Any], field_type)
            # Items inherit their own nullability from their own wrapping
            items_schema = self._get_type_schema(list_type.of_type, nullable=True, resolving=resolving)
            bson_t: str | list[str] = ["array", "null"] if nullable else "array"
            return {"bsonType": bson_t, "items": items_schema}

        # --- Scalar ---
        if is_scalar_type(field_type):
            scalar = cast(GraphQLScalarType, field_type)
            # GeoJSON without @geoType → permissive object (shape unknown at type level)
            if scalar.name == "GeoJSON":
                schema = dict(_GEOJSON_GENERIC_SCHEMA)
                if nullable:
                    schema["bsonType"] = [cast(str, schema.get("bsonType", "object")), "null"]
                return schema
            bson_scalar = GRAPHQL_SCALAR_TO_BSON.get(scalar.name, "string")
            if nullable:
                return {"bsonType": [bson_scalar, "null"]}
            return {"bsonType": bson_scalar}

        # --- Enum — always inlined, never $ref ---
        if is_enum_type(field_type):
            enum_type = cast(GraphQLEnumType, field_type)
            values = list(enum_type.values.keys())
            if nullable:
                return {"bsonType": ["string", "null"], "enum": values}
            return {"bsonType": "string", "enum": values}

        # --- Object — inline recursively ---
        if is_object_type(field_type):
            obj = cast(GraphQLObjectType, field_type)
            inner = self._build_object_schema(obj, resolving, type_key=inline_key)
            if nullable:
                inner = dict(inner)
                inner["bsonType"] = [cast(str, inner.get("bsonType", "object")), "null"]
            return inner

        # --- Interface — inline recursively ---
        if is_interface_type(field_type):
            iface = cast(GraphQLInterfaceType, field_type)
            inner = self._build_interface_schema(iface, resolving, type_key=inline_key)
            if nullable:
                inner = dict(inner)
                inner["bsonType"] = [cast(str, inner.get("bsonType", "object")), "null"]
            return inner

        # --- Union --- oneOf inline members ---
        if is_union_type(field_type):
            union = cast(GraphQLUnionType, field_type)
            inner = self._build_union_schema(union, resolving)
            if nullable:
                inner = dict(inner)
                inner["oneOf"] = list(inner.get("oneOf", [])) + [{"bsonType": "null"}]
            return inner

        log.warning(f"Unknown GraphQL type {type(field_type)}, defaulting to bsonType: string")
        return {"bsonType": "string"}

    # ------------------------------------------------------------------
    # Directive processing
    # ------------------------------------------------------------------

    def _process_directives(
        self,
        element: GraphQLField | GraphQLObjectType,
        field_type: GraphQLType | None = None,
    ) -> dict[str, Any]:
        """
        Map S2DM directives to BSON validator keywords.

        Returns ``{"field": {...}, "contained_type": {...}}`` where ``field`` applies to
        the field itself and ``contained_type`` applies to array items (e.g. ``@range``).
        Descriptions are read from GraphQL docstrings (``field.description``) in
        ``_build_field_schema``, not from ``@metadata`` — MongoDB does not support ``$comment``.
        """
        field_exts: dict[str, Any] = {}
        contained_exts: dict[str, Any] = {}

        # @noDuplicates → uniqueItems (supported by MongoDB)
        if has_given_directive(element, "noDuplicates"):
            field_exts["uniqueItems"] = True

        # @cardinality → minItems / maxItems
        if isinstance(element, GraphQLField):
            cardinality = get_cardinality(element)
            if cardinality:
                if cardinality.min is not None:
                    field_exts["minItems"] = cardinality.min
                if cardinality.max is not None:
                    field_exts["maxItems"] = cardinality.max

        # @range → minimum / maximum
        # On list fields these belong in items, not the array wrapper
        if has_given_directive(element, "range"):
            args = get_directive_arguments(element, "range")
            range_exts: dict[str, Any] = {}
            if "min" in args:
                range_exts["minimum"] = args["min"]
            if "max" in args:
                range_exts["maximum"] = args["max"]

            unwrapped = field_type
            if unwrapped and is_non_null_type(unwrapped):
                unwrapped = cast(GraphQLNonNull[Any], unwrapped).of_type
            if unwrapped and is_list_type(unwrapped):
                contained_exts.update(range_exts)
            else:
                field_exts.update(range_exts)

        return {"field": field_exts, "contained_type": contained_exts}
