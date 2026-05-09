from pathlib import Path

import pytest
from pydantic import ValidationError

from s2dm.deps.models import DependencyConfig
from s2dm.deps.resolve.common import SCHEMA_FILENAME


def test_dependency_config_rejects_duplicate_dependency_targets(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        DependencyConfig.model_validate(
            {
                "dependencies": [
                    {
                        "name": "B",
                        "version": "5.1.0",
                        "source": str(tmp_path),
                        "artifact": SCHEMA_FILENAME,
                    },
                    {
                        "name": "B",
                        "version": "5.1.0",
                        "source": str(tmp_path),
                        "artifact": SCHEMA_FILENAME,
                    },
                ]
            }
        )


def test_dependency_config_allows_same_name_with_different_versions(tmp_path: Path) -> None:
    dependency_config = DependencyConfig.model_validate(
        {
            "dependencies": [
                {
                    "name": "B",
                    "version": "5.1.0",
                    "source": str(tmp_path),
                    "artifact": SCHEMA_FILENAME,
                },
                {
                    "name": "B",
                    "version": "5.2.0",
                    "source": str(tmp_path),
                    "artifact": SCHEMA_FILENAME,
                },
            ]
        }
    )

    assert len(dependency_config.dependencies) == 2
