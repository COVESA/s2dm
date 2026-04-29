import hashlib
import shutil
from pathlib import Path

from s2dm import log
from s2dm.deps.models import (
    DependencyConfig,
    DependencyEntry,
    DependencyLockFile,
    DependencyMetadata,
    ResolvedDependencyLockEntry,
    ResolvedDependencySource,
)
from s2dm.deps.resolve.common import DEPENDENCY_LOCK_FILENAME, METADATA_FILENAME, SCHEMA_FILENAME, VENDOR_DIRECTORY
from s2dm.deps.resolve.factory import ResolverFactory


def clean_resolved_dependencies(working_directory: Path) -> None:
    """Remove lock file and vendored dependencies from the workspace."""
    lock_path = working_directory / DEPENDENCY_LOCK_FILENAME
    if lock_path.exists():
        lock_path.unlink()

    vendor_root = working_directory / VENDOR_DIRECTORY
    if vendor_root.exists():
        shutil.rmtree(vendor_root)


def resolve_dependencies(dependency_config: DependencyConfig, working_directory: Path) -> DependencyLockFile:
    """Resolve configured dependencies into the workspace vendor directory."""
    vendor_root = working_directory / VENDOR_DIRECTORY
    existing_lock_entries = _load_existing_lock_entries(working_directory / DEPENDENCY_LOCK_FILENAME)
    expected_vendor_keys = {(dependency.name, dependency.version) for dependency in dependency_config.dependencies}
    _remove_unreferenced_vendor_targets(vendor_root, expected_vendor_keys)

    seen_vendor_targets: set[tuple[str, str]] = set()
    lock_entries: list[ResolvedDependencyLockEntry] = []

    for dependency in dependency_config.dependencies:
        lock_entry = _resolve_dependency(dependency, vendor_root, seen_vendor_targets, existing_lock_entries)
        lock_entries.append(lock_entry)

    return DependencyLockFile(dependencies=lock_entries)


def _resolve_dependency(
    dependency: DependencyEntry,
    vendor_root: Path,
    seen_vendor_targets: set[tuple[str, str]],
    existing_lock_entries: dict[tuple[str, str], ResolvedDependencyLockEntry],
) -> ResolvedDependencyLockEntry:
    vendor_key = (dependency.name, dependency.version)
    if vendor_key in seen_vendor_targets:
        raise ValueError(
            f"Duplicate resolved dependency target '{dependency.name}/{dependency.version}' is not allowed"
        )
    seen_vendor_targets.add(vendor_key)

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
    if target_directory.is_dir():
        shutil.rmtree(target_directory)
        return

    target_directory.unlink()


def _build_expected_resolved_path(dependency: DependencyEntry) -> str:
    if isinstance(dependency.source, Path):
        return str((dependency.source / dependency.artifact).absolute())
    return f"{dependency.source.rstrip('/')}/releases/download/{dependency.version}/{dependency.artifact}"


def _sha256_for_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
