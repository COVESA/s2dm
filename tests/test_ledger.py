from pathlib import Path

import pytest
from graphql import DocumentNode, build_schema, parse
from modl.models import ElementKind

from s2dm.exporters.utils.schema_loader import print_schema_with_directives_preserved
from s2dm.ledger import Ledger, LedgerEntry, annotate_schema_with_ledger
from tests.ledger_common import (
    FULL_BINDINGS,
    FULL_CONCEPTS,
    FULL_CONTRACT_REFERENCES,
    FULL_CONTRACTS,
    FULL_REVISION_ASPECTS,
    FULL_REVISIONS,
    dedent_csv,
    modl_args,
)

SCHEMA_SDL = """\
type Car {
  id: ID!
  owner: Person!
}

type Person {
  id: ID!
  name: String!
}

enum DriveType {
  FWD
  RWD
  AWD
}

type Query {
  ping: String
}
"""


def _write_ledger(
    ledger_dir: Path,
    concepts: str,
    contracts: str,
    revisions: str = FULL_REVISIONS,
    bindings: str = FULL_BINDINGS,
) -> None:
    ledger_dir.mkdir(parents=True, exist_ok=True)
    (ledger_dir / "concepts.csv").write_text(concepts, encoding="utf-8")
    (ledger_dir / "contracts.csv").write_text(contracts, encoding="utf-8")
    (ledger_dir / "revisions.csv").write_text(revisions, encoding="utf-8")
    (ledger_dir / "bindings.csv").write_text(bindings, encoding="utf-8")
    (ledger_dir / "revision_aspects.csv").write_text(FULL_REVISION_ASPECTS, encoding="utf-8")
    (ledger_dir / "contract_references.csv").write_text(FULL_CONTRACT_REFERENCES, encoding="utf-8")


def _annotate(schema_sdl: str, ledger_dir: Path) -> DocumentNode:
    schema = build_schema(schema_sdl)
    annotate_schema_with_ledger(schema, Ledger.from_directory(ledger_dir))
    printed_schema = print_schema_with_directives_preserved(schema)
    return parse(printed_schema)


def test_annotate_adds_modl_to_matched_types_fields_and_enum_values(tmp_path: Path) -> None:
    ledger_dir = tmp_path / "ledger"
    _write_ledger(ledger_dir, FULL_CONCEPTS, FULL_CONTRACTS)

    annotated = _annotate(SCHEMA_SDL, ledger_dir)

    assert modl_args(annotated, "Car") == {"concept": "http://ex/concepts/0", "contract": "http://ex/contracts/0"}
    assert modl_args(annotated, "Car", "id") == {"concept": "http://ex/concepts/2", "contract": "http://ex/contracts/2"}
    assert modl_args(annotated, "Person", "name") == {
        "concept": "http://ex/concepts/5",
        "contract": "http://ex/contracts/5",
    }
    assert modl_args(annotated, "DriveType") == {
        "concept": "http://ex/concepts/6",
        "contract": "http://ex/contracts/6",
    }
    assert modl_args(annotated, "DriveType", "FWD") == {
        "concept": "http://ex/concepts/7",
        "contract": "http://ex/contracts/7",
    }


def test_annotate_ignores_query_root_type(tmp_path: Path) -> None:
    ledger_dir = tmp_path / "ledger"
    _write_ledger(ledger_dir, FULL_CONCEPTS, FULL_CONTRACTS)

    annotated = _annotate(SCHEMA_SDL, ledger_dir)

    assert modl_args(annotated, "Query") is None
    assert modl_args(annotated, "Query", "ping") is None


def test_annotate_skips_when_validation_rejects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger_dir = tmp_path / "ledger"
    _write_ledger(ledger_dir, FULL_CONCEPTS, FULL_CONTRACTS)
    monkeypatch.setattr(
        "s2dm.ledger.directives.validate_modl_annotation",
        lambda annotations, ledger: False,
    )

    annotated = _annotate(SCHEMA_SDL, ledger_dir)

    assert modl_args(annotated, "Car") is None
    assert modl_args(annotated, "Car", "id") is None


def test_annotate_adds_nothing_when_schema_type_missing_from_ledger(tmp_path: Path) -> None:
    ledger_dir = tmp_path / "ledger"
    _write_ledger(ledger_dir, FULL_CONCEPTS, FULL_CONTRACTS)
    garage_sdl = """
type Garage {
  id: ID!
}
"""

    annotated = _annotate(SCHEMA_SDL + garage_sdl, ledger_dir)

    assert modl_args(annotated, "Car") is None
    assert modl_args(annotated, "Garage") is None


def test_ledger_excludes_concept_without_contract(tmp_path: Path) -> None:
    concepts = dedent_csv(
        """
        serial,concept_uri,current_label,previous_labels,kind,status,parent_uri,instances
        0,http://ex/concepts/0,Car,,ENTITY,ACTIVE,,
        1,http://ex/concepts/1,Person,,ENTITY,ACTIVE,,
        """
    )
    contracts = dedent_csv(
        """
        serial,concept_uri,contract_uri,revision_uri,status
        0,http://ex/concepts/0,http://ex/contracts/0,http://ex/revisions/0,ACTIVE
        """
    )
    ledger_dir = tmp_path / "ledger"
    _write_ledger(ledger_dir, concepts, contracts)

    ledger = Ledger.from_directory(ledger_dir)

    assert ledger.entry_for("Car", ElementKind.ENTITY) is not None
    assert ledger.entry_for("Person", ElementKind.ENTITY) is None


def test_ledger_uses_active_contract(tmp_path: Path) -> None:
    concepts = dedent_csv(
        """
        serial,concept_uri,current_label,previous_labels,kind,status,parent_uri,instances
        0,http://ex/concepts/0,Car,,ENTITY,ACTIVE,,
        """
    )
    contracts = dedent_csv(
        """
        serial,concept_uri,contract_uri,revision_uri,status
        10,http://ex/concepts/0,http://ex/contracts/a,http://ex/revisions/0,SUPERSEDED
        0,http://ex/concepts/0,http://ex/contracts/0,http://ex/revisions/0,ACTIVE
        """
    )
    ledger_dir = tmp_path / "ledger"
    _write_ledger(ledger_dir, concepts, contracts)

    ledger = Ledger.from_directory(ledger_dir)

    assert ledger.entry_for("Car", ElementKind.ENTITY) == LedgerEntry(
        concept_uri="http://ex/concepts/0", contract_uri="http://ex/contracts/0"
    )


def test_ledger_keeps_entity_and_property_with_same_label_apart(tmp_path: Path) -> None:
    concepts = dedent_csv(
        """
        serial,concept_uri,current_label,previous_labels,kind,status,parent_uri,instances
        0,http://ex/concepts/0,Car,,ENTITY,ACTIVE,,
        1,http://ex/concepts/1,Car.id,,ENTITY,ACTIVE,,
        2,http://ex/concepts/2,Car.id,,PROPERTY,ACTIVE,http://ex/concepts/0,
        """
    )
    contracts = dedent_csv(
        """
        serial,concept_uri,contract_uri,revision_uri,status
        0,http://ex/concepts/0,http://ex/contracts/0,http://ex/revisions/0,ACTIVE
        1,http://ex/concepts/1,http://ex/contracts/1,http://ex/revisions/1,ACTIVE
        2,http://ex/concepts/2,http://ex/contracts/2,http://ex/revisions/2,ACTIVE
        """
    )
    ledger_dir = tmp_path / "ledger"
    _write_ledger(ledger_dir, concepts, contracts)

    ledger = Ledger.from_directory(ledger_dir)

    assert ledger.entry_for("Car.id", ElementKind.PROPERTY) == LedgerEntry(
        concept_uri="http://ex/concepts/2", contract_uri="http://ex/contracts/2"
    )
    assert ledger.entry_for("Car.id", ElementKind.ENTITY) == LedgerEntry(
        concept_uri="http://ex/concepts/1", contract_uri="http://ex/contracts/1"
    )
