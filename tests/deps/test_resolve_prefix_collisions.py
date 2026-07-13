from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

from s2dm.deps.models import ResolvedDependencyLockEntry
from s2dm.deps.resolve.common import METADATA_FILENAME
from s2dm.deps.resolve.resolve import PrefixCollision, get_prefix_collisions
from tests.deps.helpers import write_metadata_file


@dataclass(frozen=True)
class DependencySpec:
    name: str
    version: str
    id: str
    preferred_prefix: str | None = None


FindCollisions = Callable[[list[DependencySpec]], list[PrefixCollision]]


def _assert_collisions(
    collisions: list[PrefixCollision],
    expected: dict[tuple[str, str], set[tuple[str, str]]],
) -> dict[tuple[str, str], PrefixCollision]:
    indexed = {(c.dependency.name, c.dependency.version): c for c in collisions}
    assert set(indexed) == set(expected)
    for key, expected_conflicts in expected.items():
        actual = {(d.name, d.version) for d in indexed[key].conflicting_dependencies}
        assert actual == expected_conflicts
    return indexed


def _assert_pair(
    collisions: list[PrefixCollision],
    a: tuple[str, str],
    b: tuple[str, str],
) -> dict[tuple[str, str], PrefixCollision]:
    return _assert_collisions(collisions, {a: {b}, b: {a}})


@pytest.fixture
def find_collisions(tmp_path: Path) -> FindCollisions:
    vendor_root = tmp_path / "vendor"

    def _run(specs: list[DependencySpec]) -> list[PrefixCollision]:
        lock_entries: list[ResolvedDependencyLockEntry] = []
        for spec in specs:
            target_directory = vendor_root / spec.name / spec.version
            target_directory.mkdir(parents=True)
            write_metadata_file(
                target_directory / METADATA_FILENAME,
                name=spec.name,
                id=spec.id,
                version=spec.version,
                preferred_prefix=spec.preferred_prefix,
            )
            lock_entries.append(
                ResolvedDependencyLockEntry(
                    name=spec.name,
                    version=spec.version,
                    resolved_path=target_directory / "schema.graphql",
                    integrity="0" * 64,
                )
            )
        return get_prefix_collisions(lock_entries, vendor_root)

    return _run


def test_three_way_collision_detected_with_id_fallback(find_collisions: FindCollisions) -> None:
    collisions = find_collisions(
        [
            DependencySpec(name="A", version="1.0.0", id="urn:test:shared"),
            DependencySpec(name="B", version="1.0.0", id="urn:test:shared"),
            DependencySpec(name="C", version="1.0.0", id="urn:test:shared"),
        ]
    )

    indexed = _assert_collisions(
        collisions,
        {
            ("A", "1.0.0"): {("B", "1.0.0"), ("C", "1.0.0")},
            ("B", "1.0.0"): {("A", "1.0.0"), ("C", "1.0.0")},
            ("C", "1.0.0"): {("A", "1.0.0"), ("B", "1.0.0")},
        },
    )
    for collision in indexed.values():
        assert collision.raw_source == "urn:test:shared"
        assert collision.sanitized_prefix == "urn_test_shared"


def test_shared_id_with_distinct_preferred_prefixes_does_not_collide(
    find_collisions: FindCollisions,
) -> None:
    collisions = find_collisions(
        [
            DependencySpec(name="A", version="1.0.0", id="urn:test:shared", preferred_prefix="vehicle"),
            DependencySpec(name="B", version="1.0.0", id="urn:test:shared", preferred_prefix="powertrain"),
        ]
    )

    assert collisions == []


def test_singleton_bucket_does_not_collide_in_mixed_input(find_collisions: FindCollisions) -> None:
    collisions = find_collisions(
        [
            DependencySpec(name="A", version="1.0.0", id="urn:test:shared"),
            DependencySpec(name="B", version="1.0.0", id="urn:test:shared"),
            DependencySpec(name="C", version="1.0.0", id="urn:test:unique"),
        ]
    )

    _assert_pair(collisions, ("A", "1.0.0"), ("B", "1.0.0"))


def test_same_name_different_versions_share_id_produce_distinguishable_collisions(
    find_collisions: FindCollisions,
) -> None:
    collisions = find_collisions(
        [
            DependencySpec(name="A", version="1.0.0", id="urn:test:shared"),
            DependencySpec(name="A", version="2.0.0", id="urn:test:shared"),
        ]
    )

    _assert_pair(collisions, ("A", "1.0.0"), ("A", "2.0.0"))


@pytest.mark.parametrize(
    ("raw_prefix_a", "raw_prefix_b", "expected_sanitized_prefix"),
    [
        pytest.param("vehicle-core", "vehicle_core", "vehicle_core", id="dash_vs_underscore"),
        pytest.param("1foo", "_1foo", "_1foo", id="leading_digit"),
        pytest.param("a@@b", "a..b", "a_b", id="multiple_invalid_chars"),
    ],
)
def test_sanitization_induced_collision_detected(
    find_collisions: FindCollisions,
    raw_prefix_a: str,
    raw_prefix_b: str,
    expected_sanitized_prefix: str,
) -> None:
    collisions = find_collisions(
        [
            DependencySpec(name="A", version="1.0.0", id="urn:test:a", preferred_prefix=raw_prefix_a),
            DependencySpec(name="B", version="1.0.0", id="urn:test:b", preferred_prefix=raw_prefix_b),
        ]
    )

    indexed = _assert_pair(collisions, ("A", "1.0.0"), ("B", "1.0.0"))
    assert all(collision.sanitized_prefix == expected_sanitized_prefix for collision in collisions)
    assert indexed[("A", "1.0.0")].raw_source == raw_prefix_a
    assert indexed[("B", "1.0.0")].raw_source == raw_prefix_b
