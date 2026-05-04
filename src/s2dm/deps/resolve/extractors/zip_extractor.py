import zipfile
from pathlib import Path

from s2dm.deps.resolve.extractors.extractor import Extractor
from s2dm.deps.resolve.extractors.factory import ExtractorFactory


@ExtractorFactory.register
class ZipExtractor(Extractor):
    """ZIP archive extractor."""

    file_formats = (".zip",)

    def extract(self, archive_path: Path, extraction_directory: Path) -> None:
        """Extract the ZIP archive into the target directory."""
        if not zipfile.is_zipfile(archive_path):
            raise ValueError(f"Unsupported or invalid dependency archive format: {archive_path.name}")

        with zipfile.ZipFile(archive_path) as zip_file:
            invalid_member = zip_file.testzip()
            if invalid_member is not None:
                raise ValueError(
                    f"Dependency archive '{archive_path.name}' contains an invalid member: {invalid_member}"
                )
            zip_file.extractall(extraction_directory)
