from pathlib import Path

from graphql import build_schema

from s2dm.exporters.utils.naming_config import (
    CaseFormat,
    NamingConventionConfig,
    ValidationMode,
    load_naming_convention_config,
)
from s2dm.tools.naming_checker import check_naming_conventions


def test_type_name_violations() -> None:
    schema = build_schema("""
        type someType {
            field: String
        }

        type another_type {
            field: String
        }
    """)

    config = NamingConventionConfig.model_validate(
        {"type": {"object": CaseFormat.PASCAL_CASE}}, context={"mode": ValidationMode.CHECK}
    )
    errors = check_naming_conventions(schema, config)

    assert len(errors) == 2


def test_type_name_exception_is_not_a_violation() -> None:
    """A type name listed in exceptions is treated as compliant, even if it wouldn't match the target case."""
    schema = build_schema("""
        type AI {
            field: String
        }

        type another_type {
            field: String
        }
    """)

    config = NamingConventionConfig.model_validate(
        {"type": {"object": CaseFormat.PASCAL_CASE}, "exceptions": {"AI": "AI"}},
        context={"mode": ValidationMode.CHECK},
    )
    errors = check_naming_conventions(schema, config)

    assert len(errors) == 1
    assert "another_type" in errors[0]


def test_interface_name_violations() -> None:
    schema = build_schema("""
        interface someInterface {
            field: String
        }

        interface Another_Interface {
            field: String
        }
    """)

    config = NamingConventionConfig.model_validate(
        {"type": {"interface": CaseFormat.PASCAL_CASE}}, context={"mode": ValidationMode.CHECK}
    )
    errors = check_naming_conventions(schema, config)

    assert len(errors) == 2


def test_field_name_violations() -> None:
    schema = build_schema("""
        type SomeType {
            FieldName: String
            another_field: String
        }
    """)

    config = NamingConventionConfig.model_validate(
        {"field": {"object": CaseFormat.CAMEL_CASE}}, context={"mode": ValidationMode.CHECK}
    )
    errors = check_naming_conventions(schema, config)

    assert len(errors) == 2


def test_enum_value_violations() -> None:
    schema = build_schema("""
        enum Status {
            active
            Inactive
        }
    """)

    config = NamingConventionConfig.model_validate(
        {"enumValue": CaseFormat.MACRO_CASE}, context={"mode": ValidationMode.CHECK}
    )
    errors = check_naming_conventions(schema, config)

    assert len(errors) == 2


def test_argument_name_violations() -> None:
    schema = build_schema("""
        type Query {
            getUser(UserId: ID, user_name: String): String
        }
    """)

    config = NamingConventionConfig.model_validate(
        {"argument": {"field": CaseFormat.CAMEL_CASE}}, context={"mode": ValidationMode.CHECK}
    )
    errors = check_naming_conventions(schema, config)

    assert len(errors) == 2


def test_plural_violations() -> None:
    schema = build_schema("""
        type SomeType {
            item: [String]
            user: [String]!
        }
    """)

    config = NamingConventionConfig.model_validate({}, context={"mode": ValidationMode.CHECK})
    errors = check_naming_conventions(schema, config)

    assert len(errors) == 2


def test_no_violations() -> None:
    schema = build_schema("""
        type SomeType {
            items: [String]
            userName: String
        }

        enum Status {
            ACTIVE
            INACTIVE
        }
    """)

    config = NamingConventionConfig.model_validate(
        {
            "type": {"object": CaseFormat.PASCAL_CASE, "enum": CaseFormat.PASCAL_CASE},
            "field": {"object": CaseFormat.CAMEL_CASE},
            "enumValue": CaseFormat.MACRO_CASE,
        },
        context={"mode": ValidationMode.CHECK},
    )
    errors = check_naming_conventions(schema, config)

    assert len(errors) == 0


def test_multiple_violation_types() -> None:
    schema = build_schema("""
        type some_type {
            FieldName: String
            item: [String]
            SomeInterface: some_interface
        }

        interface some_interface {
            field: String
        }

        enum status {
            Active
        }
    """)

    config = NamingConventionConfig.model_validate(
        {
            "type": {
                "object": CaseFormat.PASCAL_CASE,
                "interface": CaseFormat.PASCAL_CASE,
                "enum": CaseFormat.PASCAL_CASE,
            },
            "field": {"object": CaseFormat.CAMEL_CASE, "interface": CaseFormat.CAMEL_CASE},
            "enumValue": CaseFormat.MACRO_CASE,
        },
        context={"mode": ValidationMode.CHECK},
    )
    errors = check_naming_conventions(schema, config)

    assert len(errors) == 7


def test_load_naming_convention_config_parses_exceptions(tmp_path: Path) -> None:
    """load_naming_convention_config parses the top-level exceptions key from YAML."""
    config_path = tmp_path / "naming.yaml"
    config_path.write_text(
        "type:\n" "  object: PascalCase\n" "exceptions:\n" "  AI: AI\n" "  VIN: VIN\n" "  PwfStatus: PWFStatus\n"
    )

    config = load_naming_convention_config(config_path)

    assert config is not None
    assert config.exceptions == {"AI": "AI", "VIN": "VIN", "PwfStatus": "PWFStatus"}
