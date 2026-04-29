import hashlib
import tarfile
import zipfile
from io import BytesIO
from pathlib import Path

import yaml

from s2dm.deps.resolve.common import METADATA_FILENAME, SCHEMA_FILENAME


def write_metadata_file(
    path: Path,
    *,
    name: str = "B",
    metadata_id: str = "urn:test:B",
    version: str = "5.1.0",
    preferred_prefix: str | None = None,
) -> None:
    metadata_payload: dict[str, str] = {
        "name": name,
        "id": metadata_id,
        "version": version,
    }
    if preferred_prefix is not None:
        metadata_payload["preferred_prefix"] = preferred_prefix
    path.write_text(yaml.safe_dump(metadata_payload, sort_keys=False), encoding="utf-8")


def write_dependency_config(
    path: Path,
    source: str | Path,
    artifact: str,
    *,
    name: str = "B",
    version: str = "5.1.0",
) -> None:
    dependency_payload = {
        "dependencies": [
            {
                "name": name,
                "version": version,
                "source": str(source),
                "artifact": artifact,
            }
        ]
    }
    path.write_text(yaml.safe_dump(dependency_payload, sort_keys=False), encoding="utf-8")


def write_dependency_lock(
    path: Path,
    *,
    resolved_path: str,
    integrity: str,
    name: str = "B",
    version: str = "5.1.0",
) -> None:
    lock_payload = {
        "dependencies": [
            {
                "name": name,
                "version": version,
                "resolved_path": resolved_path,
                "integrity": integrity,
            }
        ]
    }
    path.write_text(yaml.safe_dump(lock_payload, sort_keys=False), encoding="utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_archive(
    archive_path: Path,
    schema_name: str | None = SCHEMA_FILENAME,
    extra_graphql_name: str | None = None,
) -> None:
    schema_content = "type Query { ping: String }\n"
    metadata_content = yaml.safe_dump({"name": "B", "id": "urn:test:B", "version": "5.1.0"}, sort_keys=False)

    if archive_path.name.endswith(".zip"):
        with zipfile.ZipFile(archive_path, mode="w") as zip_file:
            if schema_name is not None:
                zip_file.writestr(schema_name, schema_content)
            zip_file.writestr(METADATA_FILENAME, metadata_content)
            if extra_graphql_name is not None:
                zip_file.writestr(extra_graphql_name, schema_content)
        return

    if archive_path.name.endswith(".tar.gz"):
        with tarfile.open(archive_path, mode="w:gz") as tar_file:
            _add_archive_members(tar_file, schema_content, metadata_content, schema_name, extra_graphql_name)
        return

    with tarfile.open(archive_path, mode="w") as tar_file:
        _add_archive_members(tar_file, schema_content, metadata_content, schema_name, extra_graphql_name)


def _add_archive_members(
    tar_file: tarfile.TarFile,
    schema_content: str,
    metadata_content: str,
    schema_name: str | None,
    extra_graphql_name: str | None,
) -> None:
    if schema_name is not None:
        schema_bytes = schema_content.encode("utf-8")
        schema_info = tarfile.TarInfo(name=schema_name)
        schema_info.size = len(schema_bytes)
        tar_file.addfile(schema_info, BytesIO(schema_bytes))

    metadata_bytes = metadata_content.encode("utf-8")
    metadata_info = tarfile.TarInfo(name=METADATA_FILENAME)
    metadata_info.size = len(metadata_bytes)
    tar_file.addfile(metadata_info, BytesIO(metadata_bytes))

    if extra_graphql_name is not None:
        extra_graphql_bytes = schema_content.encode("utf-8")
        extra_graphql_info = tarfile.TarInfo(name=extra_graphql_name)
        extra_graphql_info.size = len(extra_graphql_bytes)
        tar_file.addfile(extra_graphql_info, BytesIO(extra_graphql_bytes))


def load_yaml_file(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded
