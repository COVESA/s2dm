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
    seen_vendor_targets: set[tuple[str, str]] = set()
    lock_entries: list[ResolvedDependencyLockEntry] = []

    for dependency in dependency_config.dependencies:
        log.debug(f"Resolving dependency '{dependency.name}'")
        lock_entry = _resolve_dependency(dependency, vendor_root, seen_vendor_targets)
        lock_entries.append(lock_entry)

    return DependencyLockFile(dependencies=lock_entries)


def _resolve_dependency(
    dependency: DependencyEntry,
    vendor_root: Path,
    seen_vendor_targets: set[tuple[str, str]],
) -> ResolvedDependencyLockEntry:
    resolved_source = _resolve_dependency_source(dependency)

    metadata = DependencyMetadata.load(resolved_source.source.metadata_path)
    if dependency.name != metadata.name:
        raise ValueError(
            f"Dependency name mismatch for '{dependency.name}': metadata.yaml declares '{metadata.name}'"
        )

    vendor_key = (metadata.name, metadata.version)
    if vendor_key in seen_vendor_targets:
        raise ValueError(
            f"Duplicate resolved dependency target '{metadata.name}/{metadata.version}' is not allowed"
        )
    seen_vendor_targets.add(vendor_key)

    target_directory = vendor_root / metadata.name / metadata.version
    vendored_schema_path = target_directory / SCHEMA_FILENAME
    vendored_metadata_path = target_directory / METADATA_FILENAME
    if target_directory.exists():
        log.info(f"Skipping dependency '{metadata.name}' because vendor target already exists")
        return ResolvedDependencyLockEntry.model_validate(
            {
                "name": metadata.name,
                "version": metadata.version,
                "resolved_path": resolved_source.resolved_path,
                "integrity": _sha256_for_file(vendored_schema_path),
            }
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


def _sha256_for_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
