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
    if existing_lock_entry is not None and vendored_schema_path.is_file() and vendored_metadata_path.is_file():
        log.info(
            "Skipping dependency '%s' version '%s' because vendor target already exists",
            dependency.name,
            dependency.version,
        )
        return ResolvedDependencyLockEntry.model_validate(
            {
                "name": dependency.name,
                "version": dependency.version,
                "resolved_path": str(existing_lock_entry.resolved_path),
                "integrity": _sha256_for_file(vendored_schema_path),
            }
        )

    if target_directory.exists():
        _remove_existing_vendor_target(target_directory)

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


def _load_existing_lock_entries(lock_path: Path) -> dict[tuple[str, str], ResolvedDependencyLockEntry]:
    if not lock_path.exists():
        return {}

    lock_file = DependencyLockFile.load(lock_path)
    return {(dependency.name, dependency.version): dependency for dependency in lock_file.dependencies}


def _remove_existing_vendor_target(target_directory: Path) -> None:
    if target_directory.is_dir():
        shutil.rmtree(target_directory)
        return

    target_directory.unlink()


def _sha256_for_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
