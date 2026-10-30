"""Embedding models downloaded from Hugging Face Hub repos."""

import contextlib
from pathlib import Path

import httpx
from huggingface_hub import hf_hub_download
from huggingface_hub.errors import RemoteEntryNotFoundError
from pydantic import BaseModel, ValidationError

from s2dm.tools.embeddings.errors import ModelResolutionError
from s2dm.tools.embeddings.model_spec import ModelSourceReference
from s2dm.tools.embeddings.sources.factory import ModelSourceFactory
from s2dm.tools.embeddings.sources.source import ModelFiles, ModelSource

HUGGING_FACE_KIND = "huggingface"
DEFAULT_MODEL_REPO = "MongoDB/mdbr-leaf-ir"
DEFAULT_MODEL_REVISION = "4262131b32c3182bd06e67e92ae69d7bd66e0c5c"


class HuggingFaceReference(BaseModel):
    """A model repo on the Hugging Face Hub, pinned to a revision."""

    repo: str
    revision: str

    def to_source_reference(self) -> ModelSourceReference:
        """Build the source reference stored in the embeddings file.

        Returns:
            The reference, with ``kind`` set to the Hugging Face source.
        """
        reference_fields = {"kind": HUGGING_FACE_KIND, **self.model_dump()}
        return ModelSourceReference.model_validate(reference_fields)


DEFAULT_MODEL_REFERENCE = HuggingFaceReference(repo=DEFAULT_MODEL_REPO, revision=DEFAULT_MODEL_REVISION)


def _download_optional_repo_file(repo: str, revision: str, filename: str, directory: Path) -> None:
    """Download a repo file that some models do not publish, skipping it when the Hub reports no such file.

    Args:
        repo: Hugging Face repo id.
        revision: Repo revision to download from.
        filename: Repo-relative path of the file.
        directory: Folder the file is written into, under its repo-relative path.

    Raises:
        OSError: When the download fails for any reason other than the file being absent from the repo.
        httpx.HTTPError: When the connection drops mid-transfer and the Hub client's retries run out.
    """
    with contextlib.suppress(RemoteEntryNotFoundError):
        hf_hub_download(repo, filename, revision=revision, local_dir=directory)


@ModelSourceFactory.register
class HuggingFaceSource(ModelSource):
    """Downloads a model's files from its Hugging Face Hub repo.

    Files are stored as regular files under ``cache_root/<repo>/<revision>``, not in the Hugging Face hub cache,
    because ONNX Runtime refuses to load external weight files through the hub cache's symlinks.

    Optional files are downloaded before required ones, so a folder that holds every required file is complete,
    even when an earlier download was interrupted.
    """

    def __init__(self, reference: ModelSourceReference, cache_root: Path) -> None:
        super().__init__(reference, cache_root)

        reference_fields = reference.model_dump()
        try:
            self._hub_reference = HuggingFaceReference.model_validate(reference_fields)
        except ValidationError as error:
            raise ModelResolutionError(f"Invalid Hugging Face model reference: {error}") from error

    @classmethod
    def matches(cls, reference: ModelSourceReference) -> bool:
        return reference.kind == HUGGING_FACE_KIND

    def download(self, files: ModelFiles) -> Path:
        repo = self._hub_reference.repo
        revision = self._hub_reference.revision
        directory = self.cache_root / repo / revision

        is_cached = all((directory / filename).is_file() for filename in files.required)
        if is_cached:
            return directory

        try:
            for filename in files.optional:
                _download_optional_repo_file(repo, revision, filename, directory)

            for filename in files.required:
                hf_hub_download(repo, filename, revision=revision, local_dir=directory)
        except (OSError, httpx.HTTPError) as error:
            raise ModelResolutionError(f"Cannot download model '{repo}' at '{revision}': {error}") from error

        return directory
