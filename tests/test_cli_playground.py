from pathlib import Path
from unittest.mock import call, patch

import pytest
from click.testing import CliRunner

from s2dm.cli import cli


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    return CliRunner()


def test_playground_init_installs_at_repository_root(runner: CliRunner) -> None:
    with runner.isolated_filesystem():
        repository_dir = Path.cwd()
        playground_dir = repository_dir / "playground"
        playground_dir.mkdir()
        (playground_dir / "package.json").write_text("{}")

        with patch("s2dm.cli.subprocess.run") as run_mock:
            result = runner.invoke(cli, ["playground", "init"])

    assert result.exit_code == 0, result.output
    assert run_mock.call_args_list == [
        call(["npm", "install"], cwd=repository_dir, check=True),
        call(["npm", "run", "build"], cwd=playground_dir, check=True),
    ]


@pytest.mark.parametrize(
    ("node_modules_path", "is_launched"),
    [
        ("node_modules", True),
        ("playground/node_modules", False),
    ],
)
def test_playground_start_requires_root_node_modules(
    runner: CliRunner,
    node_modules_path: str,
    is_launched: bool,
) -> None:
    with runner.isolated_filesystem():
        Path("playground").mkdir()
        Path(node_modules_path).mkdir()

        # The failing launch stops the command at its first server process.
        with patch("s2dm.cli.subprocess.Popen", side_effect=FileNotFoundError("uvicorn")) as popen_mock:
            result = runner.invoke(cli, ["playground", "start"])

    assert result.exit_code == 1
    assert popen_mock.called is is_launched
