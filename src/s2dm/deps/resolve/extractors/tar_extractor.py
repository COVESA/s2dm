import tarfile
from pathlib import Path

from s2dm.deps.resolve.extractors.extractor import Extractor
from s2dm.deps.resolve.extractors.factory import ExtractorFactory


@ExtractorFactory.register
class TarExtractor(Extractor):
    """TAR archive extractor."""

    file_formats = (".tar", ".tar.gz", ".tgz")

    def extract(self, archive_path: Path, extraction_directory: Path) -> None:
        """Extract the TAR archive into the target directory."""
        if not tarfile.is_tarfile(archive_path):
            raise ValueError(f"Unsupported or invalid dependency archive format: {archive_path.name}")

        with tarfile.open(archive_path, mode="r:*") as tar_file:
            tar_file.extractall(extraction_directory, filter="data")
