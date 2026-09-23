from contextlib import nullcontext
from pathlib import Path
from typing import Literal

import yaml
from graphql import DocumentNode, parse
from pydantic import ValidationError

from s2dm.deps import DEPENDENCY_LOCK_FILENAME, clean_resolved_dependencies, resolve_dependencies
from s2dm.deps.compose import (
    DependencyCompositionError,
    DependencySchemaBuilder,
    DependencySchemaInput,
    DependencyTypeNameConflict,
)
from s2dm.deps.models import DependencyConfig, DependencyLockFile, DependencyMetadata, RemoteIdentityConfig
from s2dm.deps.resolve.common import (
    DEFAULT_DEPS_CONFIG_FILENAME,
    DEFAULT_IDENTITY_FILENAME,
    METADATA_FILENAME,
    SCHEMA_FILENAME,
    VENDOR_DIRECTORY,
)
from s2dm.deps.resolve.context import ResolverContext
from s2dm.deps.resolve.errors import DependencyConfigError, DependencySourceError
from s2dm.deps.resolve.providers import RemoteIdentityProvider
from s2dm.deps.resolve.resolve import validate_cached_dependency
from s2dm.deps.resolve.warnings import WarningCollector
from s2dm.exporters.utils.schema_loader import build_schema_str_with_optional_source_map
from s2dm.utils.compose import SchemaDefinition, SharedDefinitionResolver
from s2dm.utils.file import temp_file_from_content, temp_files_from_contents

DependencyStatus = Literal["not_configured", "unresolved", "resolved", "invalid"]


def get_dependency_config_path(workspace: Path) -> Path:
    return workspace / DEFAULT_DEPS_CONFIG_FILENAME


def get_dependency_identity_path(workspace: Path) -> Path:
    return workspace / DEFAULT_IDENTITY_FILENAME


def load_dependency_config(path: Path) -> DependencyConfig:
    return DependencyConfig.load(path)


def save_dependency_config(config: DependencyConfig, path: Path) -> None:
    _save_yaml_payload(path, config.model_dump(mode="json"))


def load_dependency_identity_config(path: Path) -> RemoteIdentityConfig | None:
    if not path.exists():
        return None
    return RemoteIdentityConfig.load(path)


def save_dependency_identity_config(identity_config: RemoteIdentityConfig, path: Path) -> None:
    _save_yaml_payload(path, identity_config.model_dump(mode="json"))


def delete_dependency_identity_config(path: Path) -> None:
    path.unlink(missing_ok=True)


def build_resolver_context(
    identity_config: RemoteIdentityConfig | None,
    warning_collector: WarningCollector | None = None,
) -> ResolverContext:
    remote_identity_provider = None
    if identity_config is not None:
        remote_identity_provider = RemoteIdentityProvider(identity_config)
    return ResolverContext(
        remote_identity_provider=remote_identity_provider,
        warning_collector=warning_collector,
    )


def resolve_dependency_config_to_lock_path(
    dependency_config: DependencyConfig,
    workspace: Path,
    resolver_context: ResolverContext | None = None,
    clean: bool = False,
) -> Path:
    """Resolve a dependency config and persist the resulting lock file in *workspace*."""
    clean_context = clean_resolved_dependencies(workspace) if clean else nullcontext()
    with clean_context:
        lock_file = resolve_dependencies(dependency_config, workspace, resolver_context)

    lock_path = workspace / DEPENDENCY_LOCK_FILENAME
    lock_file.save(lock_path)
    return lock_path


def load_vendored_dependency_schema_inputs(
    dependency_config: DependencyConfig,
    vendor_root: Path,
) -> list[DependencySchemaInput]:
    """Load vendored dependency schemas and metadata, applying per-dependency selections when present."""
    dependency_schema_inputs: list[DependencySchemaInput] = []
    selection_by_schema_path: dict[Path, DocumentNode] = {}

    def resolve_schema_selection(schema_path: Path) -> DocumentNode | None:
        return selection_by_schema_path.get(schema_path.resolve())

    for dependency in dependency_config.dependencies:
        dependency_vendor_directory = vendor_root / dependency.name / dependency.version
        schema_path = dependency_vendor_directory / SCHEMA_FILENAME
        metadata_path = dependency_vendor_directory / METADATA_FILENAME

        if not schema_path.is_file():
            raise ValueError(f"Vendored dependency schema does not exist: {schema_path}")
        if not metadata_path.is_file():
            raise ValueError(f"Vendored dependency metadata does not exist: {metadata_path}")

        resolved_schema_path = schema_path.resolve()
        if dependency.selection is not None:
            selection_by_schema_path[resolved_schema_path] = parse(dependency.selection.read_text(encoding="utf-8"))

        try:
            schema_content, _ = build_schema_str_with_optional_source_map(
                [resolved_schema_path],
                schema_selection_resolver=resolve_schema_selection,
            )
        except ValueError as error:
            raise ValueError(
                f"Failed to build dependency '{dependency.name}@{dependency.version}':\n{error}"
            ) from error
        dependency_schema_inputs.append(
            DependencySchemaInput(
                schema_content=schema_content,
                metadata=DependencyMetadata.load(metadata_path),
            )
        )

    if not dependency_schema_inputs:
        raise ValueError(f"No vendored dependency schemas found under {vendor_root}")

    return dependency_schema_inputs


def prepare_dependency_schemas_for_composition(
    dependency_schema_inputs: list[DependencySchemaInput],
    auto_prefix: bool,
    merge_shared_definitions: bool = False,
) -> list[Path]:
    """Build the per-dependency schema files to compose, reconciling cross-dependency conflicts.

    Definitions collide differently depending on their kind:

    - Directives and scalars are shared and cannot be prefixed. The resolver merges identical
      redeclarations into one shared block and hands the builder each dependency's types only.
    - Type names are namespaced: clashing types are prefixed, but only when ``auto_prefix`` is set.

    A conflict blocks the build when it cannot be reconciled: incompatible directive/scalar
    redeclarations always block, and type-name clashes block only without ``auto_prefix``.

    Raises:
        DependencyCompositionError: Lists every blocking conflict.
    """
    schema_definitions = [
        SchemaDefinition(
            content=dependency_schema_input.schema_content,
            source_label=dependency_schema_input.metadata.label,
        )
        for dependency_schema_input in dependency_schema_inputs
    ]
    resolver = SharedDefinitionResolver(schema_definitions, merge_shared_definitions=merge_shared_definitions)
    type_only_schema_definitions = resolver.schema_definitions_without_shared_definitions()
    type_only_inputs: list[DependencySchemaInput] = []

    schema_input_pairs = zip(dependency_schema_inputs, type_only_schema_definitions, strict=True)
    for dependency_schema_input, type_only_schema_definition in schema_input_pairs:
        if not type_only_schema_definition.content.strip():
            # Dependency only contributed shared definitions (directives/scalars/enums/Query) and
            # defines no object/interface/input/union types of its own, so there is nothing left to
            # hand to the type-name-conflict builder. Its shared definitions are still captured by
            # `resolver.resolved_definitions_sdl()` below.
            continue
        type_only_input = DependencySchemaInput(
            schema_content=type_only_schema_definition.content,
            metadata=dependency_schema_input.metadata,
        )
        type_only_inputs.append(type_only_input)

    builder = DependencySchemaBuilder(type_only_inputs)

    blocking_type_conflicts = () if auto_prefix else builder.find_conflicts()
    conflict_messages = _type_conflict_messages(blocking_type_conflicts)
    shared_conflict_messages = resolver.conflict_messages()
    conflict_messages.extend(shared_conflict_messages)
    if conflict_messages:
        raise DependencyCompositionError(conflict_messages)

    if auto_prefix:
        type_schema_files = builder.write_auto_prefixed_schema_files()
    else:
        type_schema_contents = [type_only_input.schema_content for type_only_input in type_only_inputs]
        type_schema_files = temp_files_from_contents(type_schema_contents)

    resolved_definitions_sdl = resolver.resolved_definitions_sdl()
    if not resolved_definitions_sdl:
        return type_schema_files
    resolved_definitions_file = temp_file_from_content(resolved_definitions_sdl)
    return [resolved_definitions_file, *type_schema_files]


def _type_conflict_messages(type_name_conflicts: tuple[DependencyTypeNameConflict, ...]) -> list[str]:
    return [
        f"Multiple definitions of type `{conflict.type_name}` found in "
        f"[{dependency_labels(conflict.dependencies_metadata)}]"
        for conflict in type_name_conflicts
    ]


def dependency_labels(dependencies_metadata: tuple[DependencyMetadata, ...]) -> str:
    return ", ".join(metadata.label for metadata in dependencies_metadata)


def validate_cached_dependency_workspace(
    dependency_config: DependencyConfig,
    workspace: Path,
) -> None:
    lock_path = workspace / DEPENDENCY_LOCK_FILENAME
    if not lock_path.exists():
        raise DependencyConfigError("Dependencies are unresolved. Run deps resolve first.")

    try:
        lock_file = DependencyLockFile.load(lock_path)
    except ValidationError as error:
        raise DependencyConfigError(str(error)) from error

    lock_entries_by_target = {
        (dependency.name, dependency.version): dependency for dependency in lock_file.dependencies
    }
    expected_targets = {(dependency.name, dependency.version) for dependency in dependency_config.dependencies}

    if len(lock_entries_by_target) != len(lock_file.dependencies):
        raise DependencyConfigError("Dependency lock file contains duplicate dependency targets")
    if set(lock_entries_by_target) != expected_targets:
        raise DependencyConfigError("Dependency lock file does not match configured dependencies")

    vendor_root = workspace / VENDOR_DIRECTORY
    for dependency in dependency_config.dependencies:
        validate_cached_dependency(
            dependency=dependency,
            vendor_root=vendor_root,
            existing_lock_entry=lock_entries_by_target[(dependency.name, dependency.version)],
        )


def get_dependency_status(workspace: Path) -> DependencyStatus:
    config_path = get_dependency_config_path(workspace)
    if not config_path.exists():
        return "not_configured"

    try:
        dependency_config = load_dependency_config(config_path)
    except ValidationError:
        return "invalid"

    lock_path = workspace / DEPENDENCY_LOCK_FILENAME
    if not lock_path.exists():
        return "unresolved"

    try:
        validate_cached_dependency_workspace(dependency_config, workspace)
    except (DependencyConfigError, DependencySourceError):
        return "invalid"

    return "resolved"


def _save_yaml_payload(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
