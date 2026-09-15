"""Tests for the `s2dm docs scaffold` command."""

from pathlib import Path

from click.testing import CliRunner, Result

from s2dm.docs import scaffold

SAMPLE_OPTS = [
    "--project-title",
    "My Model",
    "--project-name",
    "my-model",
    "--org-name",
    "myorg",
    "--pages-url",
    "https://myorg.github.io/my-model",
    "--github-repo-url",
    "https://github.com/myorg/my-model",
]


def _run_scaffold(runner: CliRunner, args: list[str]) -> Result:
    return runner.invoke(scaffold, args, catch_exceptions=False)


def test_scaffold_creates_output_directory(tmp_path: Path) -> None:
    """Happy path: the output directory is created and contains expected files."""
    output = tmp_path / "website"
    runner = CliRunner()
    result = _run_scaffold(runner, SAMPLE_OPTS + ["--output", str(output)])

    assert result.exit_code == 0, result.output
    assert output.is_dir()
    assert (output / "docusaurus.config.ts").exists()
    assert (output / "package.json").exists()
    assert (output / "sidebars.ts").exists()
    assert (output / "tsconfig.json").exists()
    assert (output / "custom-mdx.cjs").exists()


def test_scaffold_includes_insights_page_and_generation_pipeline(tmp_path: Path) -> None:
    """The generated website includes the self-contained Insights feature."""
    output = tmp_path / "website"
    runner = CliRunner()
    result = _run_scaffold(runner, SAMPLE_OPTS + ["--output", str(output)])

    assert result.exit_code == 0, result.output
    assert (output / "src/insights/InsightsPage.tsx").exists()
    assert (output / "src/insights/insights.module.css").exists()
    assert (output / "src/insights/cards.ts").exists()
    assert (output / "src/insights-ui/components/ConceptsBreakdown.tsx").exists()
    assert (output / "src/insights-ui/hostDefaults.tsx").exists()
    assert (output / "src/components/InsightsDetailsPane.tsx").exists()
    assert (output / "src/insights-ui/state/insightsSlice.ts").exists()
    assert (output / "src/insights-ui/selectors/concepts.ts").exists()
    assert (output / "src/insights-ui/types/concepts.ts").exists()
    assert (output / "src/insights-ui/state/insightDetailSlice.ts").exists()

    package_json = (output / "package.json").read_text()
    assert "s2dm insights export" in package_json
    assert "static/insights.json" in package_json


def test_scaffold_includes_ledger_page_and_staging_scripts(tmp_path: Path) -> None:
    """The generated website includes the self-contained Ledger feature."""
    output = tmp_path / "website"
    runner = CliRunner()
    result = _run_scaffold(runner, SAMPLE_OPTS + ["--output", str(output)])

    assert result.exit_code == 0, result.output
    assert (output / "src/ledger/LedgerPage.tsx").exists()
    assert (output / "src/ledger/ledger.module.css").exists()
    assert (output / "src/ledger/views.ts").exists()
    assert (output / "src/ledger-ui/components/RawTablesView.tsx").exists()
    assert (output / "src/ledger-ui/data/schema.ts").exists()
    # The database runs on a worker thread, which needs its own entry point.
    assert (output / "src/ledger-ui/data/ledgerWorker.ts").exists()
    assert (output / "src/ledger-ui/data/ledgerClient.ts").exists()
    assert (output / "src/ledger-ui/state/ledgerSaga.ts").exists()
    assert (output / "src/store/ledgerStore.ts").exists()

    # The database and the WebAssembly binary are staged by these two scripts.
    assert (output / "scripts/copy-ledger.js").exists()
    assert (output / "scripts/copy-sql-wasm.js").exists()

    package_json = (output / "package.json").read_text()
    assert "scripts/copy-ledger.js" in package_json
    assert "scripts/copy-sql-wasm.js" in package_json
    assert "sql.js" in package_json


def test_scaffold_substitutes_placeholders(tmp_path: Path) -> None:
    """Placeholder substitution in docusaurus.config.ts produces expected strings."""
    output = tmp_path / "website"
    runner = CliRunner()
    result = _run_scaffold(runner, SAMPLE_OPTS + ["--output", str(output)])

    assert result.exit_code == 0, result.output
    config = (output / "docusaurus.config.ts").read_text()
    assert "My Model" in config
    assert "myorg" in config
    assert "my-model" in config
    # pages_url is split into origin + base_url
    assert "https://myorg.github.io" in config
    assert "/my-model/" in config
    assert "https://github.com/myorg/my-model" in config
    # No unresolved placeholders remain
    assert "$project_title" not in config
    assert "$org_name" not in config
    assert "$project_name" not in config
    assert "$pages_origin" not in config
    assert "$pages_base_url" not in config
    assert "$github_repo_url" not in config

    package_json = (output / "package.json").read_text()
    package_lock = (output / "package-lock.json").read_text()
    assert '"name": "my-model-website"' in package_json
    assert '"name": "my-model-website"' in package_lock
    assert "$project_name" not in package_lock


def test_scaffold_refuses_existing_dir_without_force(tmp_path: Path) -> None:
    """Command exits with error when output directory exists and --force is not set."""
    output = tmp_path / "website"
    output.mkdir()
    (output / "existing.txt").write_text("keep me")

    runner = CliRunner()
    result = runner.invoke(scaffold, SAMPLE_OPTS + ["--output", str(output)])

    assert result.exit_code != 0
    # The pre-existing file must not have been removed
    assert (output / "existing.txt").exists()


def test_scaffold_force_overwrites_existing_dir(tmp_path: Path) -> None:
    """--force removes the existing output directory and recreates it."""
    output = tmp_path / "website"
    output.mkdir()
    (output / "stale.txt").write_text("old content")

    runner = CliRunner()
    result = _run_scaffold(runner, SAMPLE_OPTS + ["--output", str(output), "--force"])

    assert result.exit_code == 0, result.output
    assert output.is_dir()
    # Stale file from the previous directory must be gone
    assert not (output / "stale.txt").exists()
    # Fresh scaffold files must be present
    assert (output / "docusaurus.config.ts").exists()
