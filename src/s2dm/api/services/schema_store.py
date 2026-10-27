"""Schema text kept on disk, so clients can refer to a schema instead of resending its text.

Schema text is stored under its hash. Resolved dependencies are already on disk in the vendor
directory. Both are referenced by schema inputs and loaded as already composed.
"""

import hashlib
from pathlib import Path

from s2dm.api.config import get_api_workspace
from s2dm.api.errors import ResourceNotFoundError
from s2dm.api.models.base import SchemaReferenceInput
from s2dm.deps.resolve.common import SCHEMA_FILENAME, VENDOR_DIRECTORY
from s2dm.utils.file import write_text_atomically

SCHEMA_STORE_DIRECTORY = "schemas"


def schema_text_id(schema_text: str) -> str:
    """Return the id of schema text: its SHA-256."""
    return hashlib.sha256(schema_text.encode()).hexdigest()


def _stored_schema_path(schema_id: str) -> Path:
    return get_api_workspace() / SCHEMA_STORE_DIRECTORY / f"{schema_id}.graphql"


def store_schema_text(schema_text: str) -> str:
    """Store schema text under its id, unless it is already stored.

    Args:
        schema_text: The schema text.

    Returns:
        The schema id, used to refer to the stored text.
    """
    schema_id = schema_text_id(schema_text)
    stored_path = _stored_schema_path(schema_id)
    if not stored_path.is_file():
        # TODO: add a cleanup policy for stored schemas
        write_text_atomically(stored_path, schema_text)
    return schema_id


def _dependency_schema_path(name: str, version: str) -> Path:
    """Return the vendored schema of a dependency, refusing paths outside the vendor directory."""
    vendor_root = (get_api_workspace() / VENDOR_DIRECTORY).resolve()
    schema_path = (vendor_root / name / version / SCHEMA_FILENAME).resolve()
    if not schema_path.is_relative_to(vendor_root) or not schema_path.is_file():
        raise ResourceNotFoundError(f"No schema found for dependency '{name}' version '{version}'")
    return schema_path


def resolve_schema_reference(reference: SchemaReferenceInput) -> Path:
    """Find the file a schema reference points to.

    Args:
        reference: A stored schema id or a dependency name and version.

    Returns:
        The path of the composed schema file.

    Raises:
        ResourceNotFoundError: When the referenced schema does not exist.
    """
    if reference.type == "dependency":
        return _dependency_schema_path(reference.name, reference.version)
    stored_path = _stored_schema_path(reference.id)
    if not stored_path.is_file():
        raise ResourceNotFoundError(f"No schema stored under id '{reference.id}'")
    return stored_path
