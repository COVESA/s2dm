"""Read concept annotations from a ledger directory of CSV files."""

import csv
from dataclasses import dataclass
from pathlib import Path

from modl.models import ElementStatus

CONCEPTS_FILE = "concepts.csv"
CONTRACTS_FILE = "contracts.csv"


@dataclass(frozen=True)
class LedgerEntry:
    """A concept's ledger annotation: its URI and the URI of its contract."""

    concept_uri: str
    contract_uri: str


@dataclass(frozen=True)
class Ledger:
    """Concept annotations loaded from a ledger directory, keyed by concept label and kind.

    A label is the concept's ``current_label`` as recorded in ``concepts.csv``: a bare
    type name (e.g. ``Car``) for an entity, or ``Type.field`` (e.g. ``Car.id``) for a
    property. The kind is the concept's ``kind`` (e.g. ``ENTITY`` or ``PROPERTY``), so an
    entity and a property with the same label get separate entries. A concept becomes an
    entry once it can be paired with an active contract.
    """

    entries_by_label_and_kind: dict[tuple[str, str], LedgerEntry]
    directory: Path

    @classmethod
    def from_directory(cls, ledger_dir: Path) -> "Ledger":
        contract_uri_by_concept_uri = cls._read_active_contracts(ledger_dir / CONTRACTS_FILE)
        entries_by_label_and_kind = cls._read_concepts(ledger_dir / CONCEPTS_FILE, contract_uri_by_concept_uri)
        return cls(entries_by_label_and_kind=entries_by_label_and_kind, directory=ledger_dir)

    def entry_for(self, label: str, kind: str) -> LedgerEntry | None:
        return self.entries_by_label_and_kind.get((label, kind))

    @staticmethod
    def _read_active_contracts(contracts_path: Path) -> dict[str, str]:
        contract_uri_by_concept_uri: dict[str, str] = {}
        for row in _read_rows(contracts_path):
            if row["status"] != ElementStatus.ACTIVE:
                continue
            contract_uri_by_concept_uri.setdefault(row["concept_uri"], row["contract_uri"])
        return contract_uri_by_concept_uri

    @staticmethod
    def _read_concepts(
        concepts_path: Path, contract_uri_by_concept_uri: dict[str, str]
    ) -> dict[tuple[str, str], LedgerEntry]:
        entries_by_label_and_kind: dict[tuple[str, str], LedgerEntry] = {}
        for row in _read_rows(concepts_path):
            concept_uri = row["concept_uri"]
            contract_uri = contract_uri_by_concept_uri.get(concept_uri)
            if contract_uri is None:
                continue
            entry = LedgerEntry(concept_uri=concept_uri, contract_uri=contract_uri)
            entries_by_label_and_kind.setdefault((row["current_label"], row["kind"]), entry)
        return entries_by_label_and_kind


def _read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))
