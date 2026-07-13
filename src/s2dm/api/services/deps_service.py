"""Dependency resolution service for API endpoints."""

import shutil
from pathlib import Path

from pydantic import ValidationError

from s2dm.api.config import get_api_workspace
from s2dm.api.errors import ResourceNotFoundError, ResponseError, format_error_list
from s2dm.api.models.base import ContentInput
from s2dm.api.models.deps import (
    ApiDependencyEntry,
    DependenciesIdentities,
    DependenciesStatusResponse,
    DependencyPathInput,
    GetDependenciesConfigResponse,
    SaveDependenciesConfigRequest,
)
from s2dm.deps.helpers import (
    build_resolver_context,
    delete_dependency_identity_config,
    get_dependency_config_path,
    get_dependency_identity_path,
    get_dependency_status,
    load_dependency_config,
    load_dependency_identity_config,
    load_vendored_dependency_schema_inputs,
    prepare_dependency_schemas_for_composition,
    resolve_dependency_config_to_lock_path,
    save_dependency_config,
    save_dependency_identity_config,
    validate_cached_dependency_workspace,
)
from s2dm.deps.models import DependencyConfig, DependencyEntry, RemoteIdentityConfig
from s2dm.deps.models.deps_file import GRAPHQL_FILE_EXTENSIONS
from s2dm.deps.resolve.common import DEPENDENCY_LOCK_FILENAME, SCHEMA_FILENAME, VENDOR_DIRECTORY
from s2dm.deps.resolve.errors import DependencyConfigError
from s2dm.deps.resolve.warnings import ListWarningCollector
from s2dm.exporters.utils.schema_loader import compose_schemas_to_string


def save_dependencies_config(config: SaveDependenciesConfigRequest) -> None:
    """Store dependency configuration in the API workspace."""
    api_workspace = get_api_workspace()
    dependency_config = _build_dependency_config(config, api_workspace)
    if not dependency_config.dependencies:
        _clear_resolved_dependency_workspace(api_workspace)
    save_dependency_config(dependency_config, get_dependency_config_path(api_workspace))


def load_dependencies_config() -> GetDependenciesConfigResponse:
    """Load stored dependency configuration from the API workspace."""
    api_workspace = get_api_workspace()
    config_path = get_dependency_config_path(api_workspace)
    if not config_path.exists():
        raise ResourceNotFoundError("Dependency config is not stored")

    dependency_config = _load_dependency_config_file(config_path)
    selections_directory = _get_api_selection_directory(api_workspace)
    vendor_root = api_workspace / VENDOR_DIRECTORY

    try:
        api_dependencies: list[ApiDependencyEntry] = []
        for dependency_entry in dependency_config.dependencies:
            selection = _build_api_selection_input(dependency_entry.selection, selections_directory)
            schema_path = vendor_root / dependency_entry.name / dependency_entry.version / SCHEMA_FILENAME
            schema_content = None
            if schema_path.is_file():
                schema_content = schema_path.read_text(encoding="utf-8")

            api_dependency = ApiDependencyEntry(
                name=dependency_entry.name,
                version=dependency_entry.version,
                source=dependency_entry.source,
                artifact=dependency_entry.artifact,
                selection=selection,
            )
            if schema_content is not None:
                api_dependency.schema_content = schema_content

            api_dependencies.append(api_dependency)

        return GetDependenciesConfigResponse(dependencies=api_dependencies)
    except (OSError, ValidationError, ValueError) as error:
        raise DependencyConfigError(str(error)) from error


def save_dependencies_identities(identities: DependenciesIdentities) -> None:
    """Store dependency identities in the API workspace."""
    api_workspace = get_api_workspace()
    remote_identity_config = _build_remote_identity_config(identities)
    save_dependency_identity_config(remote_identity_config, get_dependency_identity_path(api_workspace))


def load_dependencies_identities() -> DependenciesIdentities:
    """Load stored dependency identities from the API workspace."""
    api_workspace = get_api_workspace()
    identity_path = get_dependency_identity_path(api_workspace)
    identity_config = load_dependency_identity_config(identity_path)
    if identity_config is None:
        raise ResourceNotFoundError("Dependency identities are not stored")

    return DependenciesIdentities(identities=identity_config.identities)


def delete_dependencies_identities() -> None:
    """Delete stored dependency identities from the API workspace if present."""
    delete_dependency_identity_config(get_dependency_identity_path(get_api_workspace()))


def load_dependencies_status() -> DependenciesStatusResponse:
    """Evaluate dependency resolution status in the API-managed workspace."""
    status = get_dependency_status(get_api_workspace())
    return DependenciesStatusResponse(status=status)


def resolve_api_dependencies(clean: bool) -> list[str]:
    """Resolve dependencies in the API-managed workspace."""
    api_workspace = get_api_workspace()
    warnings: list[str] = []
    identity_config = load_dependency_identity_config(get_dependency_identity_path(api_workspace))
    resolver_context = build_resolver_context(identity_config, warning_collector=ListWarningCollector(warnings))
    dependency_config = _load_stored_dependency_config(api_workspace)

    resolve_dependency_config_to_lock_path(
        dependency_config,
        api_workspace,
        resolver_context,
        clean,
    )
    return warnings


def build_api_dependencies(auto_prefix: bool) -> str:
    """Compose vendored dependency schemas in the API-managed workspace."""
    api_workspace = get_api_workspace()
    dependency_config = _load_stored_dependency_config(api_workspace)
    validate_cached_dependency_workspace(dependency_config, api_workspace)
    vendor_root = api_workspace / VENDOR_DIRECTORY

    selected_schema_contents, dependency_schema_inputs = load_vendored_dependency_schema_inputs(
        dependency_config,
        vendor_root,
    )
    schema_paths, type_name_conflicts = prepare_dependency_schemas_for_composition(
        dependency_schema_inputs,
        selected_schema_contents,
        auto_prefix,
    )
    if type_name_conflicts and not auto_prefix:
        conflict_messages = [
            "Multiple "
            f"`{conflict.type_name}` types found in "
            f"[{', '.join(f'{dependency.name}@{dependency.version}' for dependency in conflict.dependencies_metadata)}]"
            for conflict in type_name_conflicts
        ]
        raise ResponseError(
            format_error_list("Dependency build failed due to conflicting type definitions", conflict_messages)
        )
    return compose_schemas_to_string(
        schemas=schema_paths,
        root_type=None,
        selection_query=None,
        naming_config=None,
        expanded_instances=False,
    )


def _build_dependency_config(config: SaveDependenciesConfigRequest, api_workspace: Path) -> DependencyConfig:
    selections_directory = _get_api_selection_directory(api_workspace)
    config_directory = None if config.config_directory is None else Path(config.config_directory)
    try:
        dependency_config = DependencyConfig(
            dependencies=[
                DependencyEntry(
                    name=dependency_entry.name,
                    version=dependency_entry.version,
                    source=dependency_entry.source,
                    artifact=dependency_entry.artifact,
                    selection=_resolve_selection_path(
                        dependency_entry.selection,
                        dependency_entry.name,
                        dependency_entry.version,
                        selections_directory,
                        config_directory,
                    ),
                )
                for dependency_entry in config.dependencies
            ]
        )
    except (OSError, ValidationError, ValueError) as error:
        raise DependencyConfigError(str(error)) from error
    _cleanup_orphaned_selection_files(dependency_config, selections_directory)
    return dependency_config


def _build_remote_identity_config(identities: DependenciesIdentities) -> RemoteIdentityConfig:
    try:
        return RemoteIdentityConfig(identities=identities.identities)
    except ValidationError as error:
        raise DependencyConfigError(str(error)) from error


def _load_stored_dependency_config(api_workspace: Path) -> DependencyConfig:
    config_path = get_dependency_config_path(api_workspace)
    if not config_path.exists():
        raise ResourceNotFoundError("Dependency config is not stored")
    return _load_dependency_config_file(config_path)


def _load_dependency_config_file(config_path: Path) -> DependencyConfig:
    try:
        return load_dependency_config(config_path)
    except ValidationError as error:
        raise DependencyConfigError(str(error)) from error


def _resolve_selection_path(
    selection: DependencyPathInput | ContentInput | None,
    dependency_name: str,
    dependency_version: str,
    selections_directory: Path,
    config_directory: Path | None,
) -> Path | None:
    if selection is None:
        return None

    if selection.type == "path":
        selection_content = _resolve_external_selection_path(Path(selection.path), config_directory).read_text(
            encoding="utf-8"
        )
    else:
        selection_content = selection.content

    return _write_managed_selection_file(
        selection_content,
        dependency_name,
        dependency_version,
        selections_directory,
    )


def _resolve_external_selection_path(selection_path: Path, config_directory: Path | None) -> Path:
    if not selection_path.is_absolute():
        if config_directory is None:
            raise ValueError("Relative dependency selection paths require `config_directory`")
        selection_path = config_directory / selection_path

    if selection_path.suffix.lower() not in GRAPHQL_FILE_EXTENSIONS:
        raise ValueError("Dependency selection must be a .graphql or .gql file")
    if not selection_path.is_file():
        raise ValueError(f"Dependency selection file does not exist: {selection_path}")
    return selection_path.resolve()


def _write_managed_selection_file(
    selection_content: str,
    dependency_name: str,
    dependency_version: str,
    selections_directory: Path,
) -> Path:
    selections_directory.mkdir(parents=True, exist_ok=True)
    selection_path = selections_directory / f"{dependency_name}-{dependency_version}.graphql"
    selection_path.write_text(selection_content, encoding="utf-8")
    return selection_path


def _build_api_selection_input(
    selection_path: Path | None,
    selections_directory: Path,
) -> DependencyPathInput | ContentInput | None:
    if selection_path is None:
        return None

    resolved_selection_path = selection_path.resolve()
    if not resolved_selection_path.is_file():
        raise ValueError(f"Dependency selection file does not exist: {resolved_selection_path}")

    if resolved_selection_path.is_relative_to(selections_directory.resolve()):
        return ContentInput(type="content", content=resolved_selection_path.read_text(encoding="utf-8"))
    return DependencyPathInput(type="path", path=str(resolved_selection_path))


def _cleanup_orphaned_selection_files(dependency_config: DependencyConfig, selections_directory: Path) -> None:
    if not selections_directory.exists():
        return

    resolved_selections_directory = selections_directory.resolve()
    managed_selection_paths = {
        resolved_selection_path
        for dependency in dependency_config.dependencies
        if dependency.selection is not None
        and (resolved_selection_path := dependency.selection.resolve()).is_relative_to(resolved_selections_directory)
    }
    for selection_path in selections_directory.iterdir():
        if not selection_path.is_file():
            continue
        resolved_selection_path = selection_path.resolve()
        if resolved_selection_path in managed_selection_paths:
            continue
        selection_path.unlink()


def _clear_resolved_dependency_workspace(api_workspace: Path) -> None:
    (api_workspace / DEPENDENCY_LOCK_FILENAME).unlink(missing_ok=True)
    shutil.rmtree(api_workspace / VENDOR_DIRECTORY, ignore_errors=True)


def _get_api_selection_directory(api_workspace: Path) -> Path:
    return api_workspace / "selections"
