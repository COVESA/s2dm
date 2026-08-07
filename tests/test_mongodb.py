"""Unit tests for the MongoDB BSON Schema exporter."""

import json
from pathlib import Path
from typing import Any, cast

import pytest
from graphql import build_schema

from s2dm.exporters.mongodb.mongodb import transform
from s2dm.exporters.mongodb.transformer import MongoDBTransformer


def make_transformer(schema_str: str) -> MongoDBTransformer:
    return MongoDBTransformer(build_schema(schema_str))


def make_transform(schema_str: str) -> dict[str, dict[str, Any]]:
    return transform(build_schema(schema_str))


# ---------------------------------------------------------------------------
# BSON scalar type mapping
# ---------------------------------------------------------------------------


class TestBSONTypeMapping:
    BASE = "type Query {{ ping: String }}\ntype TestTypeA {{ {field} }}"

    def _field_schema(self, field_decl: str) -> dict[str, Any]:
        schema_str = self.BASE.format(field=field_decl)
        t = make_transformer(schema_str)
        result = t.transform()
        return cast(dict[str, Any], result["TestTypeA"]["properties"]["testField"])

    def test_string_maps_to_string(self) -> None:
        s = self._field_schema("testField: String!")
        assert s["bsonType"] == "string"

    def test_int_maps_to_int(self) -> None:
        s = self._field_schema("testField: Int!")
        assert s["bsonType"] == "int"

    def test_float_maps_to_double(self) -> None:
        s = self._field_schema("testField: Float!")
        assert s["bsonType"] == "double"

    def test_boolean_maps_to_bool(self) -> None:
        s = self._field_schema("testField: Boolean!")
        assert s["bsonType"] == "bool"

    def test_id_maps_to_objectid(self) -> None:
        s = self._field_schema("testField: ID!")
        assert s["bsonType"] == "objectId"

    def test_int8_maps_to_int(self) -> None:
        schema_str = "scalar Int8\n" "type Query { ping: String }\n" "type TestTypeA { testField: Int8! }"
        t = make_transformer(schema_str)
        result = t.transform()
        assert result["TestTypeA"]["properties"]["testField"]["bsonType"] == "int"

    def test_int64_maps_to_long(self) -> None:
        schema_str = "scalar Int64\n" "type Query { ping: String }\n" "type TestTypeA { testField: Int64! }"
        t = make_transformer(schema_str)
        result = t.transform()
        assert result["TestTypeA"]["properties"]["testField"]["bsonType"] == "long"

    def test_uint64_maps_to_long(self) -> None:
        schema_str = "scalar UInt64\n" "type Query { ping: String }\n" "type TestTypeA { testField: UInt64! }"
        t = make_transformer(schema_str)
        result = t.transform()
        assert result["TestTypeA"]["properties"]["testField"]["bsonType"] == "long"


# ---------------------------------------------------------------------------
# Nullable / non-null handling
# ---------------------------------------------------------------------------


class TestNullableHandling:
    BASE = "type Query {{ ping: String }}\ntype TestTypeA {{ {field} }}"

    def _field(self, decl: str) -> dict[str, Any]:
        t = make_transformer(self.BASE.format(field=decl))
        return cast(dict[str, Any], t.transform()["TestTypeA"]["properties"]["testField"])

    def test_nullable_scalar_uses_list_bsontype(self) -> None:
        s = self._field("testField: String")
        assert isinstance(s["bsonType"], list)
        assert "string" in s["bsonType"]
        assert "null" in s["bsonType"]

    def test_non_null_scalar_uses_string_bsontype(self) -> None:
        s = self._field("testField: String!")
        assert s["bsonType"] == "string"

    def test_nullable_field_not_in_required(self) -> None:
        t = make_transformer(self.BASE.format(field="testField: String"))
        schema = t.transform()["TestTypeA"]
        assert "testField" not in schema.get("required", [])

    def test_non_null_field_in_required(self) -> None:
        t = make_transformer(self.BASE.format(field="testField: String!"))
        schema = t.transform()["TestTypeA"]
        assert "testField" in schema["required"]

    def test_nullable_object_bsontype_includes_null(self) -> None:
        schema_str = (
            "type Query { ping: String }\n"
            "type TestTypeA { testFieldNested: TestTypeB }\n"
            "type TestTypeB { testFieldA: String }"
        )
        t = make_transformer(schema_str)
        nested = t.transform()["TestTypeA"]["properties"]["testFieldNested"]
        assert isinstance(nested["bsonType"], list)
        assert "object" in nested["bsonType"]
        assert "null" in nested["bsonType"]

    def test_non_null_object_bsontype_is_string(self) -> None:
        schema_str = (
            "type Query { ping: String }\n"
            "type TestTypeA { testFieldNested: TestTypeB! }\n"
            "type TestTypeB { testFieldA: String }"
        )
        t = make_transformer(schema_str)
        nested = t.transform()["TestTypeA"]["properties"]["testFieldNested"]
        assert nested["bsonType"] == "object"


# ---------------------------------------------------------------------------
# Enum inlining (no $ref)
# ---------------------------------------------------------------------------


class TestEnumInlining:
    SCHEMA = """
        enum AnEnumA { VALUE_1 VALUE_2 VALUE_3 }
        type Query { ping: String }
        type TestTypeA { testFieldEnum: AnEnumA testFieldEnumRequired: AnEnumA! }
    """

    def test_enum_field_has_bsontype_string_or_list(self) -> None:
        t = make_transformer(self.SCHEMA)
        bson_t = t.transform()["TestTypeA"]["properties"]["testFieldEnum"]["bsonType"]
        if isinstance(bson_t, list):
            assert "string" in bson_t
        else:
            assert bson_t == "string"

    def test_enum_required_field_has_values(self) -> None:
        t = make_transformer(self.SCHEMA)
        f = t.transform()["TestTypeA"]["properties"]["testFieldEnumRequired"]
        assert f["enum"] == ["VALUE_1", "VALUE_2", "VALUE_3"]

    def test_no_ref_in_enum_field(self) -> None:
        t = make_transformer(self.SCHEMA)
        field_str = json.dumps(t.transform()["TestTypeA"]["properties"]["testFieldEnum"])
        assert "$ref" not in field_str

    def test_enum_type_not_a_top_level_entry(self) -> None:
        t = make_transformer(self.SCHEMA)
        assert "AnEnumA" not in t.transform()

    def test_nullable_enum_bsontype_includes_null(self) -> None:
        t = make_transformer(self.SCHEMA)
        bson_t = t.transform()["TestTypeA"]["properties"]["testFieldEnum"]["bsonType"]
        assert isinstance(bson_t, list)
        assert "null" in bson_t

    def test_non_null_enum_bsontype_is_string(self) -> None:
        t = make_transformer(self.SCHEMA)
        assert t.transform()["TestTypeA"]["properties"]["testFieldEnumRequired"]["bsonType"] == "string"


# ---------------------------------------------------------------------------
# Nested object inlining (no $ref)
# ---------------------------------------------------------------------------


class TestNestedTypeInlining:
    SCHEMA = """
        type Query { ping: String }
        type TestTypeA { testFieldNested: TestTypeB! }
        type TestTypeB { testFieldA: String! testFieldB: Int }
    """

    def test_nested_type_inlined(self) -> None:
        t = make_transformer(self.SCHEMA)
        nested = t.transform()["TestTypeA"]["properties"]["testFieldNested"]
        assert nested["bsonType"] == "object"
        assert "testFieldA" in nested["properties"]
        assert "testFieldB" in nested["properties"]

    def test_no_ref_in_output(self) -> None:
        t = make_transformer(self.SCHEMA)
        assert "$ref" not in json.dumps(t.transform())

    def test_nested_required_preserved(self) -> None:
        t = make_transformer(self.SCHEMA)
        nested = t.transform()["TestTypeA"]["properties"]["testFieldNested"]
        assert nested.get("required") == ["testFieldA"]


# ---------------------------------------------------------------------------
# List fields
# ---------------------------------------------------------------------------


class TestListFields:
    SCHEMA = """
        type Query { ping: String }
        type TestTypeA {
          testFieldList: [TestTypeB]
          testFieldListRequired: [TestTypeB]!
        }
        type TestTypeB { testFieldA: String }
    """

    def test_nullable_list_bsontype_is_array_null(self) -> None:
        t = make_transformer(self.SCHEMA)
        f = t.transform()["TestTypeA"]["properties"]["testFieldList"]
        assert isinstance(f["bsonType"], list)
        assert "array" in f["bsonType"]
        assert "null" in f["bsonType"]

    def test_non_null_list_bsontype_is_array(self) -> None:
        t = make_transformer(self.SCHEMA)
        f = t.transform()["TestTypeA"]["properties"]["testFieldListRequired"]
        assert f["bsonType"] == "array"

    def test_list_has_items(self) -> None:
        t = make_transformer(self.SCHEMA)
        f = t.transform()["TestTypeA"]["properties"]["testFieldList"]
        assert "items" in f

    def test_scalar_list_items_bsontype(self) -> None:
        schema_str = "type Query { ping: String }\ntype TestTypeA { testFieldList: [String]! }"
        t = make_transformer(schema_str)
        f = t.transform()["TestTypeA"]["properties"]["testFieldList"]
        assert f["bsonType"] == "array"
        # items are nullable list-item (wrapping is nullable by default in GraphQL)
        items_bson = f["items"]["bsonType"]
        assert "string" in items_bson if isinstance(items_bson, list) else items_bson == "string"


# ---------------------------------------------------------------------------
# Directive support
# ---------------------------------------------------------------------------


class TestDirectives:
    DIRECTIVES = (
        "directive @range(min: Float, max: Float) on FIELD_DEFINITION\n"
        "directive @noDuplicates on FIELD_DEFINITION\n"
        "directive @cardinality(min: Int, max: Int) on FIELD_DEFINITION\n"
        "directive @metadata(comment: String, vssType: String) on FIELD_DEFINITION | OBJECT\n"
        "type Query { ping: String }\n"
    )

    def _transform(self, body: str) -> dict[str, dict[str, Any]]:
        return make_transformer(self.DIRECTIVES + body).transform()

    def test_range_adds_minimum_maximum(self) -> None:
        result = self._transform("type TestTypeB { testFieldRange: Float @range(min: 0.0, max: 100.0) }")
        f = result["TestTypeB"]["properties"]["testFieldRange"]
        assert f["minimum"] == 0.0
        assert f["maximum"] == 100.0

    def test_no_duplicates_adds_unique_items(self) -> None:
        result = self._transform("type TestTypeB { testFieldNoDups: [String] @noDuplicates }")
        assert result["TestTypeB"]["properties"]["testFieldNoDups"]["uniqueItems"] is True

    def test_cardinality_adds_min_max_items(self) -> None:
        result = self._transform("type TestTypeB { testFieldCardinality: [String] @cardinality(min: 1, max: 5) }")
        f = result["TestTypeB"]["properties"]["testFieldCardinality"]
        assert f["minItems"] == 1
        assert f["maxItems"] == 5

    def test_graphql_docstring_emitted_as_description(self) -> None:
        result = self._transform('type TestTypeB { """A descriptive comment""" testFieldMeta: String }')
        f = result["TestTypeB"]["properties"]["testFieldMeta"]
        assert f["description"] == "A descriptive comment"

    def test_range_on_list_field_goes_into_items(self) -> None:
        result = self._transform("type TestTypeB { testFieldList: [Float] @range(min: 1.0, max: 9.0) }")
        f = result["TestTypeB"]["properties"]["testFieldList"]
        assert "minimum" not in f
        assert f["items"]["minimum"] == 1.0
        assert f["items"]["maximum"] == 9.0

    def test_no_dollar_comment_in_output(self) -> None:
        """$comment is not supported in MongoDB $jsonSchema."""
        result = self._transform('type TestTypeB { """note""" testFieldMeta: String }')
        assert '"$comment"' not in json.dumps(result)


# ---------------------------------------------------------------------------
# Exclusions
# ---------------------------------------------------------------------------


class TestExclusions:
    def test_query_type_excluded(self) -> None:
        schema_str = "type Query { ping: String }\ntype TestTypeA { testFieldA: String }"
        assert "Query" not in make_transformer(schema_str).transform()

    def test_mutation_type_excluded(self) -> None:
        schema_str = (
            "type Query { ping: String }\n"
            "type Mutation { doSomething: String }\n"
            "type TestTypeA { testFieldA: String }"
        )
        assert "Mutation" not in make_transformer(schema_str).transform()

    def test_instance_tag_type_excluded(self) -> None:
        schema_str = (
            "directive @instanceTag on OBJECT\n"
            "type Query { ping: String }\n"
            "type AnInstanceTag @instanceTag { row: String }\n"
            "type TestTypeA { testFieldA: String }"
        )
        assert "AnInstanceTag" not in make_transformer(schema_str).transform()

    def test_scalar_type_excluded_as_top_level(self) -> None:
        schema_str = "scalar Int64\n" "type Query { ping: String }\n" "type TestTypeA { testField: Int64 }"
        assert "Int64" not in make_transformer(schema_str).transform()

    def test_enum_type_excluded_as_top_level(self) -> None:
        schema_str = (
            "enum AnEnumA { VALUE_1 VALUE_2 }\n" "type Query { ping: String }\n" "type TestTypeA { testField: AnEnumA }"
        )
        assert "AnEnumA" not in make_transformer(schema_str).transform()


# ---------------------------------------------------------------------------
# Top-level schema structure
# ---------------------------------------------------------------------------


class TestJsonSchemaWrapping:
    def test_each_type_has_bsontype_object(self) -> None:
        schema_str = (
            "type Query { ping: String }\n"
            "type TestTypeA { testFieldA: String }\n"
            "type TestTypeB { testFieldB: Int }"
        )
        result = make_transform(schema_str)
        for type_name in ("TestTypeA", "TestTypeB"):
            assert type_name in result
            assert result[type_name]["bsonType"] == "object"

    def test_no_json_schema_wrapper(self) -> None:
        schema_str = "type Query { ping: String }\ntype TestTypeA { testFieldA: String }"
        result = make_transform(schema_str)
        assert "$jsonSchema" not in json.dumps(result)

    def test_no_ref_anywhere_in_output(self) -> None:
        schema_str = (
            "type Query { ping: String }\n"
            "type TestTypeA { testFieldNested: TestTypeB }\n"
            "type TestTypeB { testFieldA: String }"
        )
        assert "$ref" not in json.dumps(make_transform(schema_str))

    def test_no_dollar_schema_or_definitions_in_output(self) -> None:
        schema_str = "type Query { ping: String }\ntype TestTypeA { testFieldA: String }"
        dumped = json.dumps(make_transform(schema_str))
        assert '"$schema"' not in dumped
        assert '"definitions"' not in dumped

    def test_no_integer_type_in_output(self) -> None:
        """MongoDB does not support the JSON Schema 'integer' type; must use bsonType int/long."""
        schema_str = "type Query { ping: String }\ntype TestTypeA { testFieldA: Int! }"
        dumped = json.dumps(make_transform(schema_str))
        assert '"type": "integer"' not in dumped
        assert '"type":"integer"' not in dumped


# ---------------------------------------------------------------------------
# Circular reference detection
# ---------------------------------------------------------------------------


class TestCircularReference:
    def test_circular_reference_raises_value_error(self) -> None:
        schema_str = (
            "type Query { ping: String }\n"
            "type TestTypeA { testFieldB: TestTypeB }\n"
            "type TestTypeB { testFieldA: TestTypeA }\n"
        )
        with pytest.raises(ValueError, match="Circular reference"):
            make_transformer(schema_str).transform()

    def test_self_reference_raises_value_error(self) -> None:
        schema_str = "type Query { ping: String }\n" "type TestTypeA { testFieldSelf: TestTypeA }\n"
        with pytest.raises(ValueError, match="Circular reference"):
            make_transformer(schema_str).transform()


# ---------------------------------------------------------------------------
# GeoJSON scalar with @geoType directive
# ---------------------------------------------------------------------------


class TestGeoJSON:
    DIRECTIVES = (
        "enum GeoJSONShape { POINT MULTIPOINT LINESTRING MULTILINESTRING POLYGON MULTIPOLYGON }\n"
        "directive @geoType(shape: GeoJSONShape!) on FIELD_DEFINITION\n"
        "scalar GeoJSON\n"
        "type Query { ping: String }\n"
    )

    def _transform(self, body: str) -> dict[str, dict[str, Any]]:
        return make_transformer(self.DIRECTIVES + body).transform()

    # --- POINT ---

    def test_point_bsontype_object(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON! @geoType(shape: POINT) }")
        f = result["TestTypeA"]["properties"]["geo"]
        assert f["bsonType"] == "object"

    def test_point_required_fields(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON! @geoType(shape: POINT) }")
        f = result["TestTypeA"]["properties"]["geo"]
        assert set(f["required"]) == {"type", "coordinates"}

    def test_point_type_enum(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON! @geoType(shape: POINT) }")
        f = result["TestTypeA"]["properties"]["geo"]
        assert f["properties"]["type"]["enum"] == ["Point"]

    def test_point_coordinates_array_of_double(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON! @geoType(shape: POINT) }")
        coords = result["TestTypeA"]["properties"]["geo"]["properties"]["coordinates"]
        assert coords["bsonType"] == "array"
        assert coords["items"]["bsonType"] == "double"
        assert coords["minItems"] == 2
        assert coords["maxItems"] == 2

    def test_nullable_point_includes_null(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON @geoType(shape: POINT) }")
        bson_t = result["TestTypeA"]["properties"]["geo"]["bsonType"]
        assert isinstance(bson_t, list)
        assert "object" in bson_t
        assert "null" in bson_t

    def test_nullable_point_not_in_required(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON @geoType(shape: POINT) }")
        assert "geo" not in result["TestTypeA"].get("required", [])

    def test_non_null_point_in_required(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON! @geoType(shape: POINT) }")
        assert "geo" in result["TestTypeA"]["required"]

    # --- Shape-specific type enums ---

    def test_linestring_type_enum(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON! @geoType(shape: LINESTRING) }")
        f = result["TestTypeA"]["properties"]["geo"]
        assert f["properties"]["type"]["enum"] == ["LineString"]

    def test_polygon_type_enum(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON! @geoType(shape: POLYGON) }")
        f = result["TestTypeA"]["properties"]["geo"]
        assert f["properties"]["type"]["enum"] == ["Polygon"]

    def test_multipoint_type_enum(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON! @geoType(shape: MULTIPOINT) }")
        f = result["TestTypeA"]["properties"]["geo"]
        assert f["properties"]["type"]["enum"] == ["MultiPoint"]

    def test_multilinestring_type_enum(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON! @geoType(shape: MULTILINESTRING) }")
        f = result["TestTypeA"]["properties"]["geo"]
        assert f["properties"]["type"]["enum"] == ["MultiLineString"]

    def test_multipolygon_type_enum(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON! @geoType(shape: MULTIPOLYGON) }")
        f = result["TestTypeA"]["properties"]["geo"]
        assert f["properties"]["type"]["enum"] == ["MultiPolygon"]

    # --- No @geoType → generic permissive schema ---

    def test_no_geo_type_directive_gives_permissive_schema(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON! }")
        f = result["TestTypeA"]["properties"]["geo"]
        assert f["bsonType"] == "object"
        assert "type" in f["properties"]
        assert "coordinates" in f["properties"]
        # No enum constraint on type
        assert "enum" not in f["properties"]["type"]

    def test_no_geo_type_nullable_includes_null(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON }")
        bson_t = result["TestTypeA"]["properties"]["geo"]["bsonType"]
        assert isinstance(bson_t, list)
        assert "null" in bson_t

    def test_geo_json_not_top_level_entry(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON! @geoType(shape: POINT) }")
        assert "GeoJSON" not in result

    def test_no_ref_in_geojson_output(self) -> None:
        result = self._transform("type TestTypeA { geo: GeoJSON! @geoType(shape: POINT) }")
        assert "$ref" not in json.dumps(result)


# ---------------------------------------------------------------------------
# additionalProperties config
# ---------------------------------------------------------------------------

_NESTED_SCHEMA = """
    type Query { q: String }
    type Parent { child: Child nested: Nested }
    type Child { name: String }
    type Nested { value: Int }
"""


class TestAdditionalPropertiesConfig:
    """Tests for --properties-config / additional_props_false behaviour."""

    def _transform_with_cfg(self, schema_str: str, cfg: frozenset[str]) -> dict[str, dict[str, Any]]:
        from graphql import build_schema

        return MongoDBTransformer(build_schema(schema_str), cfg).transform()

    def test_no_config_no_additional_properties_key(self) -> None:
        result = self._transform_with_cfg(_NESTED_SCHEMA, frozenset())
        assert result["Parent"]["additionalProperties"] is True
        assert result["Child"]["additionalProperties"] is True

    def test_bare_type_name_sets_top_level(self) -> None:
        result = self._transform_with_cfg(_NESTED_SCHEMA, frozenset({"Parent"}))
        assert result["Parent"]["additionalProperties"] is False
        # child top-level entry is not in config → defaults to true
        assert result["Child"]["additionalProperties"] is True

    def test_bare_type_name_child_unaffected(self) -> None:
        """Top-level Child not listed → additionalProperties: true even when inlined in Parent."""
        result = self._transform_with_cfg(_NESTED_SCHEMA, frozenset({"Parent"}))
        child_inline = cast(dict[str, Any], result["Parent"]["properties"]["child"])
        assert child_inline["additionalProperties"] is True

    def test_dot_path_applies_to_inline_object(self) -> None:
        result = self._transform_with_cfg(_NESTED_SCHEMA, frozenset({"Parent.child"}))
        child_inline = cast(dict[str, Any], result["Parent"]["properties"]["child"])
        assert child_inline["additionalProperties"] is False

    def test_dot_path_does_not_affect_top_level_child(self) -> None:
        """Parent.child config → only the inline occurrence is affected; Child top-level gets true."""
        result = self._transform_with_cfg(_NESTED_SCHEMA, frozenset({"Parent.child"}))
        # Child appears as top-level too; it gets true (default)
        assert result["Child"]["additionalProperties"] is True

    def test_multiple_keys_independent(self) -> None:
        result = self._transform_with_cfg(_NESTED_SCHEMA, frozenset({"Child", "Parent.nested"}))
        # Child top-level gets additionalProperties: false
        assert result["Child"]["additionalProperties"] is False
        # Parent.nested inline gets it
        nested_inline = cast(dict[str, Any], result["Parent"]["properties"]["nested"])
        assert nested_inline["additionalProperties"] is False
        # Parent itself gets true (default)
        assert result["Parent"]["additionalProperties"] is True

    def test_nullable_inline_also_gets_flag(self) -> None:
        """Nullable nested objects are inlined via _get_type_schema which must propagate key."""
        schema_str = """
            type Query { q: String }
            type Parent { child: Child }
            type Child { x: String }
        """
        result = self._transform_with_cfg(schema_str, frozenset({"Parent.child"}))
        child_inline = cast(dict[str, Any], result["Parent"]["properties"]["child"])
        assert child_inline["additionalProperties"] is False
        # bsonType must still be ["object", "null"] because field is nullable
        assert "null" in child_inline["bsonType"]


class TestLoadPropertiesConfig:
    """Tests for load_properties_config()."""

    def test_loads_bare_type_names(self, tmp_path: Path) -> None:
        from s2dm.exporters.mongodb.mongodb import load_properties_config

        f = tmp_path / "cfg.yaml"
        f.write_text("- Address\n- ChargingStation\n")
        result = load_properties_config(f)
        assert result == frozenset({"Address", "ChargingStation"})

    def test_loads_dot_paths(self, tmp_path: Path) -> None:
        from s2dm.exporters.mongodb.mongodb import load_properties_config

        f = tmp_path / "cfg.yaml"
        f.write_text("- Address.street\n- ChargingStation.address\n")
        result = load_properties_config(f)
        assert result == frozenset({"Address.street", "ChargingStation.address"})

    def test_mixed_entries(self, tmp_path: Path) -> None:
        from s2dm.exporters.mongodb.mongodb import load_properties_config

        f = tmp_path / "cfg.yaml"
        f.write_text("- Address\n- ChargingStation.address\n")
        result = load_properties_config(f)
        assert result == frozenset({"Address", "ChargingStation.address"})

    def test_rejects_non_list_file(self, tmp_path: Path) -> None:
        from s2dm.exporters.mongodb.mongodb import load_properties_config

        f = tmp_path / "cfg.yaml"
        f.write_text("key: value\n")
        with pytest.raises(ValueError, match="must be a YAML sequence"):
            load_properties_config(f)

    def test_rejects_invalid_path_format(self, tmp_path: Path) -> None:
        from s2dm.exporters.mongodb.mongodb import load_properties_config

        f = tmp_path / "cfg.yaml"
        f.write_text("- a.b.c\n")
        with pytest.raises(ValueError, match="Invalid properties-config entry"):
            load_properties_config(f)

    def test_rejects_non_string_entry(self, tmp_path: Path) -> None:
        from s2dm.exporters.mongodb.mongodb import load_properties_config

        f = tmp_path / "cfg.yaml"
        f.write_text("- 42\n")
        with pytest.raises(ValueError, match="must be strings"):
            load_properties_config(f)


class TestPropertiesConfigValidation:
    """Tests for schema-level validation of properties-config entries."""

    def _validate(self, schema_str: str, cfg: frozenset[str]) -> None:
        from graphql import build_schema

        MongoDBTransformer(build_schema(schema_str), cfg).transform()

    _SCHEMA = """
        type Query { q: String }
        type Parent { child: Child }
        type Child { name: String }
        enum Status { ACTIVE INACTIVE }
    """

    def test_valid_bare_type_passes(self) -> None:
        self._validate(self._SCHEMA, frozenset({"Parent"}))

    def test_valid_dot_path_passes(self) -> None:
        self._validate(self._SCHEMA, frozenset({"Parent.child"}))

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="'NonExistent': type 'NonExistent' does not exist"):
            self._validate(self._SCHEMA, frozenset({"NonExistent"}))

    def test_unknown_field_raises(self) -> None:
        with pytest.raises(ValueError, match="'Parent' has no field 'missing'"):
            self._validate(self._SCHEMA, frozenset({"Parent.missing"}))

    def test_non_object_type_raises(self) -> None:
        with pytest.raises(ValueError, match="'Status' is not an object or interface type"):
            self._validate(self._SCHEMA, frozenset({"Status"}))

    def test_multiple_errors_reported_together(self) -> None:
        with pytest.raises(ValueError) as exc_info:
            self._validate(self._SCHEMA, frozenset({"NonExistent", "Parent.missing"}))
        msg = str(exc_info.value)
        assert "NonExistent" in msg
        assert "Parent.missing" in msg

    def test_empty_config_skips_validation(self) -> None:
        """Empty config must not raise even if called with an otherwise valid schema."""
        self._validate(self._SCHEMA, frozenset())
