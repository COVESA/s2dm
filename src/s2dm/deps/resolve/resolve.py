import hashlib
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from graphql import GraphQLError

from s2dm import log
from s2dm.deps.models import (
    DependencyConfig,
    DependencyEntry,
    DependencyLockFile,
    DependencyMetadata,
    ResolvedDependencyLockEntry,
    ResolvedDependencySource,
)
from s2dm.deps.naming import sanitize_prefix
from s2dm.deps.resolve.common import DEPENDENCY_LOCK_FILENAME, METADATA_FILENAME, SCHEMA_FILENAME, VENDOR_DIRECTORY
from s2dm.deps.resolve.factory import ResolverFactory
from s2dm.exporters.utils.schema_loader import check_correct_schema


@dataclass
class CleanDependencyBackup:
    """Temporary backup for a clean dependency resolution."""

    lock_path: Path
    vendor_root: Path
    lock_backup_path: Path | None
    vendor_backup_path: Path | None

    def commit(self) -> None:
        """Delete backups after a successful clean dependency resolution."""
        if self.lock_backup_path is not None and self.lock_backup_path.exists():
            self.lock_backup_path.unlink()
        if self.vendor_backup_path is not None and self.vendor_backup_path.exists():
            shutil.rmtree(self.vendor_backup_path)

    def restore(self) -> None:
        """Restore backups after a failed clean dependency resolution."""
        _remove_path_if_exists(self.lock_path)
        _remove_path_if_exists(self.vendor_root)

        if self.lock_backup_path is not None and self.lock_backup_path.exists():
            self.lock_backup_path.rename(self.lock_path)
        if self.vendor_backup_path is not None and self.vendor_backup_path.exists():
            self.vendor_root.parent.mkdir(parents=True, exist_ok=True)
            self.vendor_backup_path.rename(self.vendor_root)


@dataclass(frozen=True)
class PrefixCollision:
    """A dependency whose sanitized prefix/id collides with one or more others."""

    dependency: ResolvedDependencyLockEntry
    sanitized_prefix: str
    raw_source: str
    conflicting_dependencies: tuple[ResolvedDependencyLockEntry, ...]


@contextmanager
def clean_resolved_dependencies(working_directory: Path) -> Iterator[None]:
    """Temporarily remove lock file and vendored dependencies, restoring them on failure."""
    backup = _begin_clean_resolved_dependencies(working_directory)
    try:
        yield
    except BaseException as error:
        try:
            backup.restore()
        except OSError as restore_error:
            raise RuntimeError(
                f"Dependency clean restore failed after resolution error: {error}; restore error: {restore_error}"
            ) from restore_error
        raise
    else:
        backup.commit()


def _begin_clean_resolved_dependencies(working_directory: Path) -> CleanDependencyBackup:
    lock_path = working_directory / DEPENDENCY_LOCK_FILENAME
    vendor_root = working_directory / VENDOR_DIRECTORY
    backup_suffix = uuid4().hex
    lock_backup_path = None
    vendor_backup_path = None

    if lock_path.exists():
        lock_backup_path = lock_path.with_name(f"{lock_path.name}.clean-backup.{backup_suffix}")
        lock_path.rename(lock_backup_path)

    if vendor_root.exists():
        vendor_backup_path = vendor_root.with_name(f"{vendor_root.name}.clean-backup.{backup_suffix}")
        vendor_root.rename(vendor_backup_path)

    return CleanDependencyBackup(
        lock_path=lock_path,
        vendor_root=vendor_root,
        lock_backup_path=lock_backup_path,
        vendor_backup_path=vendor_backup_path,
    )


def resolve_dependencies(dependency_config: DependencyConfig, working_directory: Path) -> DependencyLockFile:
    """Resolve configured dependencies into the workspace vendor directory."""
    vendor_root = working_directory / VENDOR_DIRECTORY
    existing_lock_entries = _load_existing_lock_entries(working_directory / DEPENDENCY_LOCK_FILENAME)
    expected_vendor_keys = {(dependency.name, dependency.version) for dependency in dependency_config.dependencies}
    _remove_unreferenced_vendor_targets(vendor_root, expected_vendor_keys)

    lock_entries: list[ResolvedDependencyLockEntry] = []

    for dependency in dependency_config.dependencies:
        lock_entry = _resolve_dependency(dependency, vendor_root, existing_lock_entries)
        lock_entries.append(lock_entry)

    warn_on_prefix_collisions(lock_entries, vendor_root)

    return DependencyLockFile(dependencies=lock_entries)


def get_prefix_collisions(
    lock_entries: list[ResolvedDependencyLockEntry],
    vendor_root: Path,
) -> list[PrefixCollision]:
    """Detect dependencies whose sanitized prefix/id matches another's."""
    sanitized_per_entry: list[tuple[str, str]] = []
    indices_by_sanitized: dict[str, list[int]] = {}

    for index, entry in enumerate(lock_entries):
        metadata_path = vendor_root / entry.name / entry.version / METADATA_FILENAME
        metadata = DependencyMetadata.load(metadata_path)
        raw_prefix = metadata.preferred_prefix or metadata.id
        sanitized = sanitize_prefix(raw_prefix)
        sanitized_per_entry.append((sanitized, raw_prefix))
        indices_by_sanitized.setdefault(sanitized, []).append(index)

    collisions: list[PrefixCollision] = []
    for index, entry in enumerate(lock_entries):
        sanitized, raw_prefix = sanitized_per_entry[index]
        conflicting_dependencies = tuple(
            lock_entries[other_index] for other_index in indices_by_sanitized[sanitized] if other_index != index
        )
        if conflicting_dependencies:
            collisions.append(
                PrefixCollision(
                    dependency=entry,
                    sanitized_prefix=sanitized,
                    raw_source=raw_prefix,
                    conflicting_dependencies=conflicting_dependencies,
                )
            )
    return collisions


def warn_on_prefix_collisions(lock_entries: list[ResolvedDependencyLockEntry], vendor_root: Path) -> None:
    """Warn when multiple dependencies share the same sanitized prefix/id."""
    prefix_collisions = get_prefix_collisions(lock_entries, vendor_root)
    for collision in prefix_collisions:
        quoted_conflicts = ", ".join(f"'{dep.name}@{dep.version}'" for dep in collision.conflicting_dependencies)
        log.warning(
            f"Dependency '{collision.dependency.name}@{collision.dependency.version}' "
            f"resolves prefix '{collision.sanitized_prefix}' (from '{collision.raw_source}') "
            f"which conflicts with: {quoted_conflicts}. "
            f"This might cause issues when type names conflict resolution is applied."
        )


def _resolve_dependency(
    dependency: DependencyEntry,
    vendor_root: Path,
    existing_lock_entries: dict[tuple[str, str], ResolvedDependencyLockEntry],
) -> ResolvedDependencyLockEntry:
    vendor_key = (dependency.name, dependency.version)
    target_directory = vendor_root / dependency.name / dependency.version
    vendored_schema_path = target_directory / SCHEMA_FILENAME
    vendored_metadata_path = target_directory / METADATA_FILENAME

    existing_lock_entry = existing_lock_entries.get(vendor_key)
    if target_directory.exists():
        lock_entry = _resolve_cached_dependency(
            dependency=dependency,
            target_directory=target_directory,
            schema_path=vendored_schema_path,
            metadata_path=vendored_metadata_path,
            existing_lock_entry=existing_lock_entry,
        )
        log.info(
            f"Skipping dependency '{dependency.name}' version '{dependency.version}' "
            "because vendor target already exists"
        )
        return lock_entry

    log.info(f"Resolving dependency '{dependency.name}' version '{dependency.version}'")
    resolved_source = _resolve_dependency_source(dependency)

    metadata = DependencyMetadata.load(resolved_source.source.metadata_path)
    if dependency.name != metadata.name:
        raise ValueError(f"Dependency name mismatch for '{dependency.name}': metadata.yaml declares '{metadata.name}'")
    if dependency.version != metadata.version:
        raise ValueError(
            f"Dependency version mismatch for '{dependency.name}': metadata.yaml declares '{metadata.version}'"
        )
    _validate_dependency_schema(resolved_source.source.schema_path, dependency.name, dependency.version)

    target_directory.mkdir(parents=True, exist_ok=False)

    shutil.copy2(resolved_source.source.schema_path, vendored_schema_path)
    shutil.copy2(resolved_source.source.metadata_path, vendored_metadata_path)

    return ResolvedDependencyLockEntry.model_validate(
        {
            "name": metadata.name,
            "version": metadata.version,
            "resolved_path": resolved_source.resolved_path,
            "integrity": _sha256_for_file(vendored_schema_path),
        }
    )


def _resolve_dependency_source(dependency: DependencyEntry) -> ResolvedDependencySource:
    resolver = ResolverFactory.create_resolver(dependency)
    return resolver.resolve(dependency)


def _resolve_cached_dependency(
    dependency: DependencyEntry,
    target_directory: Path,
    schema_path: Path,
    metadata_path: Path,
    existing_lock_entry: ResolvedDependencyLockEntry | None,
) -> ResolvedDependencyLockEntry:
    if not target_directory.is_dir():
        raise ValueError(f"Cached dependency target must be a directory: {target_directory}")
    if not schema_path.is_file():
        raise ValueError(f"Cached dependency '{dependency.name}/{dependency.version}' is missing {SCHEMA_FILENAME}")
    if not metadata_path.is_file():
        raise ValueError(f"Cached dependency '{dependency.name}/{dependency.version}' is missing {METADATA_FILENAME}")

    metadata = DependencyMetadata.load(metadata_path)
    if dependency.name != metadata.name:
        raise ValueError(
            f"Cached dependency '{dependency.name}/{dependency.version}' metadata.yaml declares name '{metadata.name}'"
        )
    if dependency.version != metadata.version:
        raise ValueError(
            f"Cached dependency '{dependency.name}/{dependency.version}' metadata.yaml declares version "
            f"'{metadata.version}'"
        )

    expected_resolved_path = _build_expected_resolved_path(dependency)
    schema_integrity = _sha256_for_file(schema_path)
    if existing_lock_entry is None:
        return ResolvedDependencyLockEntry.model_validate(
            {
                "name": dependency.name,
                "version": dependency.version,
                "resolved_path": expected_resolved_path,
                "integrity": schema_integrity,
            }
        )

    if existing_lock_entry.name != dependency.name:
        raise ValueError(
            f"Lock entry for cached dependency '{dependency.name}/{dependency.version}' declares name "
            f"'{existing_lock_entry.name}'"
        )
    if existing_lock_entry.version != dependency.version:
        raise ValueError(
            f"Lock entry for cached dependency '{dependency.name}/{dependency.version}' declares version "
            f"'{existing_lock_entry.version}'"
        )
    if str(existing_lock_entry.resolved_path) != expected_resolved_path:
        raise ValueError(
            f"Cached dependency '{dependency.name}/{dependency.version}' resolved_path does not match deps file"
        )
    if existing_lock_entry.integrity != schema_integrity:
        raise ValueError(
            f"Cached dependency '{dependency.name}/{dependency.version}' schema integrity does not match lock file"
        )

    return existing_lock_entry


def _load_existing_lock_entries(lock_path: Path) -> dict[tuple[str, str], ResolvedDependencyLockEntry]:
    if not lock_path.exists():
        return {}

    lock_file = DependencyLockFile.load(lock_path)
    return {(dependency.name, dependency.version): dependency for dependency in lock_file.dependencies}


def _remove_unreferenced_vendor_targets(vendor_root: Path, expected_vendor_keys: set[tuple[str, str]]) -> None:
    if not vendor_root.exists():
        return

    for dependency_directory in vendor_root.iterdir():
        if not dependency_directory.is_dir():
            continue
        for version_directory in dependency_directory.iterdir():
            if not version_directory.is_dir():
                continue
            vendor_key = (dependency_directory.name, version_directory.name)
            if vendor_key not in expected_vendor_keys:
                _remove_existing_vendor_target(version_directory)
        if not any(dependency_directory.iterdir()):
            dependency_directory.rmdir()


def _remove_existing_vendor_target(target_directory: Path) -> None:
    _remove_path_if_exists(target_directory)


def _remove_path_if_exists(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def _build_expected_resolved_path(dependency: DependencyEntry) -> str:
    if isinstance(dependency.source, Path):
        return str((dependency.source / dependency.artifact).absolute())
    return f"{dependency.source.rstrip('/')}/releases/download/{dependency.version}/{dependency.artifact}"


def _validate_dependency_schema(schema_path: Path, dependency_name: str, dependency_version: str) -> None:
    dependency_label = f"{dependency_name}/{dependency_version}"
    try:
        schema_errors = check_correct_schema(schema_path)
    except GraphQLError:
        raise ValueError(f"Dependency '{dependency_label}' schema is invalid: {schema_path}") from None

    if schema_errors:
        raise ValueError(f"Dependency '{dependency_label}' schema is invalid: {schema_path}")


def _sha256_for_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
