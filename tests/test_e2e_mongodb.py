"""End-to-end tests for the MongoDB BSON Schema exporter."""

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from s2dm.cli import cli
from s2dm.exporters.mongodb import translate_to_mongodb
from s2dm.exporters.utils.schema_loader import load_and_process_schema

MONGODB_TEST_SCHEMA = Path(__file__).parent / "data" / "mongodb" / "test_schema.graphql"


class TestMongoDBE2E:
    @pytest.fixture
    def schema_paths(self, spec_directory: Path) -> list[Path]:
        """Combined spec directives + mongodb test schema."""
        return [spec_directory, MONGODB_TEST_SCHEMA]

    @pytest.fixture
    def validators(self, schema_paths: list[Path]) -> dict[str, dict[str, Any]]:
        """Load and transform to validators dict."""
        annotated_schema, _, _ = load_and_process_schema(
            schema_paths=schema_paths,
            naming_config_path=None,
            selection_query_path=None,
            root_type=None,
            expanded_instances=False,
        )
        return translate_to_mongodb(annotated_schema)

    # ------------------------------------------------------------------
    # Structure checks
    # ------------------------------------------------------------------

    def test_top_level_types_exported(self, validators: dict[str, dict[str, Any]]) -> None:
        assert "TestTypeA" in validators
        assert "TestTypeB" in validators

    def test_enums_not_top_level(self, validators: dict[str, dict[str, Any]]) -> None:
        assert "AnEnumA" not in validators
        assert "AnEnumB" not in validators

    def test_query_type_not_exported(self, validators: dict[str, dict[str, Any]]) -> None:
        assert "Query" not in validators

    def test_each_type_has_bsontype_object(self, validators: dict[str, dict[str, Any]]) -> None:
        for name in ("TestTypeA", "TestTypeB"):
            assert validators[name]["bsonType"] == "object", f"Missing bsonType for {name}"

    def test_no_json_schema_wrapper(self, validators: dict[str, dict[str, Any]]) -> None:
        assert "$jsonSchema" not in json.dumps(validators)

    def test_no_ref_anywhere(self, validators: dict[str, dict[str, Any]]) -> None:
        assert "$ref" not in json.dumps(validators), "Found $ref — not supported in MongoDB $jsonSchema"

    def test_no_schema_keyword(self, validators: dict[str, dict[str, Any]]) -> None:
        dumped = json.dumps(validators)
        assert '"$schema"' not in dumped
        assert '"definitions"' not in dumped

    def test_no_integer_type(self, validators: dict[str, dict[str, Any]]) -> None:
        """MongoDB does not support JSON Schema 'integer' type."""
        dumped = json.dumps(validators)
        assert '"type": "integer"' not in dumped
        assert '"type":"integer"' not in dumped

    # ------------------------------------------------------------------
    # Scalar / BSON type assertions
    # ------------------------------------------------------------------

    def test_id_required_maps_to_objectid(self, validators: dict[str, dict[str, Any]]) -> None:
        props = validators["TestTypeA"]["properties"]
        assert props["testFieldIdRequired"]["bsonType"] == "objectId"

    def test_nullable_id_includes_null(self, validators: dict[str, dict[str, Any]]) -> None:
        props = validators["TestTypeA"]["properties"]
        bson_t = props["testFieldId"]["bsonType"]
        assert isinstance(bson_t, list)
        assert "objectId" in bson_t
        assert "null" in bson_t

    def test_int8_maps_to_int(self, validators: dict[str, dict[str, Any]]) -> None:
        props = validators["TestTypeA"]["properties"]
        bson_t = props["testFieldInt8"]["bsonType"]
        if isinstance(bson_t, list):
            assert "int" in bson_t
        else:
            assert bson_t == "int"

    def test_int64_maps_to_long(self, validators: dict[str, dict[str, Any]]) -> None:
        props = validators["TestTypeA"]["properties"]
        bson_t = props["testFieldInt64"]["bsonType"]
        if isinstance(bson_t, list):
            assert "long" in bson_t
        else:
            assert bson_t == "long"

    # ------------------------------------------------------------------
    # Required fields
    # ------------------------------------------------------------------

    def test_required_fields_collected(self, validators: dict[str, dict[str, Any]]) -> None:
        required = validators["TestTypeA"].get("required", [])
        for field in (
            "testFieldIdRequired",
            "testFieldStringRequired",
            "testFieldIntRequired",
            "testFieldNestedRequired",
            "testFieldListRequired",
            "testFieldEnumRequired",
        ):
            assert field in required, f"Expected '{field}' in required"

    def test_nullable_fields_not_in_required(self, validators: dict[str, dict[str, Any]]) -> None:
        required = validators["TestTypeA"].get("required", [])
        for field in ("testFieldId", "testFieldString", "testFieldNested", "testFieldEnum"):
            assert field not in required, f"Did not expect '{field}' in required"

    # ------------------------------------------------------------------
    # Enum inlining
    # ------------------------------------------------------------------

    def test_enum_required_field_inlined_with_values(self, validators: dict[str, dict[str, Any]]) -> None:
        props = validators["TestTypeA"]["properties"]
        f = props["testFieldEnumRequired"]
        assert f["bsonType"] == "string"
        assert set(f["enum"]) == {"VALUE_1", "VALUE_2", "VALUE_3"}

    def test_nullable_enum_inlined_with_null(self, validators: dict[str, dict[str, Any]]) -> None:
        props = validators["TestTypeA"]["properties"]
        bson_t = props["testFieldEnum"]["bsonType"]
        assert isinstance(bson_t, list)
        assert "null" in bson_t

    # ------------------------------------------------------------------
    # Nested type inlining
    # ------------------------------------------------------------------

    def test_nested_type_inlined_no_ref(self, validators: dict[str, dict[str, Any]]) -> None:
        props = validators["TestTypeA"]["properties"]
        nested = props["testFieldNestedRequired"]
        assert nested["bsonType"] == "object"
        assert "properties" in nested
        assert "testFieldRange" in nested["properties"]

    def test_nullable_nested_type_includes_null(self, validators: dict[str, dict[str, Any]]) -> None:
        props = validators["TestTypeA"]["properties"]
        bson_t = props["testFieldNested"]["bsonType"]
        assert isinstance(bson_t, list)
        assert "object" in bson_t
        assert "null" in bson_t

    # ------------------------------------------------------------------
    # Directives
    # ------------------------------------------------------------------

    def test_range_directive(self, validators: dict[str, dict[str, Any]]) -> None:
        props = validators["TestTypeB"]["properties"]
        f = props["testFieldRange"]
        assert f["minimum"] == 0.0
        assert f["maximum"] == 100.0

    def test_no_duplicates_directive(self, validators: dict[str, dict[str, Any]]) -> None:
        props = validators["TestTypeB"]["properties"]
        assert props["testFieldNoDups"]["uniqueItems"] is True

    def test_cardinality_directive(self, validators: dict[str, dict[str, Any]]) -> None:
        props = validators["TestTypeB"]["properties"]
        f = props["testFieldCardinality"]
        assert f["minItems"] == 1
        assert f["maxItems"] == 5

    def test_graphql_docstring_emitted_as_description(self, validators: dict[str, dict[str, Any]]) -> None:
        props = validators["TestTypeB"]["properties"]
        assert props["testFieldMeta"]["description"] == "A descriptive comment"

    def test_metadata_does_not_use_dollar_comment(self, validators: dict[str, dict[str, Any]]) -> None:
        """$comment is not supported by MongoDB $jsonSchema."""
        assert '"$comment"' not in json.dumps(validators)

    # ------------------------------------------------------------------
    # CLI — default mode (single output.json)
    # ------------------------------------------------------------------

    def test_cli_default_mode_creates_output_json(self, tmp_path: Path, spec_directory: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "export",
                "mongodb",
                "--schema",
                str(spec_directory),
                "--schema",
                str(MONGODB_TEST_SCHEMA),
                "--output",
                str(tmp_path / "out"),
            ],
        )
        assert result.exit_code == 0, result.output
        out_file = tmp_path / "out" / "output.json"
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert "TestTypeA" in data
        assert "TestTypeB" in data

    def test_cli_default_mode_no_ref(self, tmp_path: Path, spec_directory: Path) -> None:
        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "export",
                "mongodb",
                "--schema",
                str(spec_directory),
                "--schema",
                str(MONGODB_TEST_SCHEMA),
                "--output",
                str(tmp_path / "out"),
            ],
        )
        assert "$ref" not in (tmp_path / "out" / "output.json").read_text()

    def test_cli_default_mode_no_modular_single_files(self, tmp_path: Path, spec_directory: Path) -> None:
        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "export",
                "mongodb",
                "--schema",
                str(spec_directory),
                "--schema",
                str(MONGODB_TEST_SCHEMA),
                "--output",
                str(tmp_path / "out"),
            ],
        )
        assert not (tmp_path / "out" / "TestTypeA.json").exists()

    # ------------------------------------------------------------------
    # CLI — modular mode (one file per type)
    # ------------------------------------------------------------------

    def test_cli_modular_creates_per_type_files(self, tmp_path: Path, spec_directory: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "export",
                "mongodb",
                "--schema",
                str(spec_directory),
                "--schema",
                str(MONGODB_TEST_SCHEMA),
                "--output",
                str(tmp_path / "out"),
                "--modular",
            ],
        )
        assert result.exit_code == 0, result.output
        assert (tmp_path / "out" / "TestTypeA.json").exists()
        assert (tmp_path / "out" / "TestTypeB.json").exists()

    def test_cli_modular_no_output_json(self, tmp_path: Path, spec_directory: Path) -> None:
        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "export",
                "mongodb",
                "--schema",
                str(spec_directory),
                "--schema",
                str(MONGODB_TEST_SCHEMA),
                "--output",
                str(tmp_path / "out"),
                "--modular",
            ],
        )
        assert not (tmp_path / "out" / "output.json").exists()

    def test_cli_modular_each_file_has_bare_bson_schema(self, tmp_path: Path, spec_directory: Path) -> None:
        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "export",
                "mongodb",
                "--schema",
                str(spec_directory),
                "--schema",
                str(MONGODB_TEST_SCHEMA),
                "--output",
                str(tmp_path / "out"),
                "--modular",
            ],
        )
        for type_name in ("TestTypeA", "TestTypeB"):
            data = json.loads((tmp_path / "out" / f"{type_name}.json").read_text())
            assert "$jsonSchema" not in data, f"Unexpected $jsonSchema wrapper in {type_name}.json"
            assert data["bsonType"] == "object"

    def test_cli_modular_no_enum_files(self, tmp_path: Path, spec_directory: Path) -> None:
        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "export",
                "mongodb",
                "--schema",
                str(spec_directory),
                "--schema",
                str(MONGODB_TEST_SCHEMA),
                "--output",
                str(tmp_path / "out"),
                "--modular",
            ],
        )
        assert not (tmp_path / "out" / "AnEnumA.json").exists()
        assert not (tmp_path / "out" / "AnEnumB.json").exists()

    # ------------------------------------------------------------------
    # GeoJSON
    # ------------------------------------------------------------------

    def test_geo_point_has_precise_bson_schema(self, validators: dict[str, dict[str, Any]]) -> None:
        props = validators["TestTypeA"]["properties"]
        f = props["testFieldGeoPointRequired"]
        assert f["bsonType"] == "object"
        assert set(f["required"]) == {"type", "coordinates"}
        assert f["properties"]["type"]["enum"] == ["Point"]
        coords = f["properties"]["coordinates"]
        assert coords["bsonType"] == "array"
        assert coords["items"]["bsonType"] == "double"
        assert coords["minItems"] == 2
        assert coords["maxItems"] == 2

    def test_geo_point_nullable_includes_null(self, validators: dict[str, dict[str, Any]]) -> None:
        bson_t = validators["TestTypeA"]["properties"]["testFieldGeoPoint"]["bsonType"]
        assert isinstance(bson_t, list)
        assert "object" in bson_t
        assert "null" in bson_t

    def test_geo_polygon_has_polygon_type_enum(self, validators: dict[str, dict[str, Any]]) -> None:
        f = validators["TestTypeA"]["properties"]["testFieldGeoPolygon"]
        assert f["properties"]["type"]["enum"] == ["Polygon"]

    def test_geo_no_shape_is_permissive(self, validators: dict[str, dict[str, Any]]) -> None:
        f = validators["TestTypeA"]["properties"]["testFieldGeoNoShape"]
        assert "object" in (f["bsonType"] if isinstance(f["bsonType"], list) else [f["bsonType"]])
        # No enum constraint on type property
        assert "enum" not in f["properties"]["type"]

    def test_geo_fields_have_no_ref(self, validators: dict[str, dict[str, Any]]) -> None:
        geo_props = {k: v for k, v in validators["TestTypeA"]["properties"].items() if "geo" in k.lower() or "Geo" in k}
        assert "$ref" not in json.dumps(geo_props)
