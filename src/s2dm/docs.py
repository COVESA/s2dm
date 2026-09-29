import shutil
import string
import sys
from pathlib import Path
from urllib.parse import urlparse

import rich_click as click

from s2dm import log

TEMPLATE_DIR = Path(__file__).parent / "templates" / "docs-website"

# Host-agnostic React components shared with the playground. Vendored into the scaffolded
# website so it stays self-contained, and reachable there through the `@insights-ui` and
# `@ledger-ui` aliases.
INSIGHTS_UI_DIR = Path(__file__).parent / "templates" / "insights-ui"
LEDGER_UI_DIR = Path(__file__).parent / "templates" / "ledger-ui"

TEMPLATED_FILES = {"docusaurus.config.ts", "package-lock.json", "package.json"}

# Each shared template's `package.json` only exists to make the directory an npm workspace member
# of this repository. The scaffolded site reaches the vendored copies through path aliases instead.
SHARED_UI_EXCLUDED_FILES = {"package.json"}


def copy_template_tree(
    source_dir: Path,
    destination_dir: Path,
    substitutions: dict[str, str],
    excluded_files: set[str] | None = None,
) -> None:
    """Copy a template tree, substituting placeholders in the files that carry them.

    Args:
        source_dir: Template tree to copy from. `node_modules` entries are skipped.
        destination_dir: Directory the tree is copied into. Created if absent.
        substitutions: Placeholder values applied to files named in `TEMPLATED_FILES`.
        excluded_files: File names to leave out of the copy.
    """
    skipped_names = excluded_files or set()
    for source_file in sorted(source_dir.rglob("*")):
        if source_file.is_dir() or "node_modules" in source_file.parts:
            continue
        if source_file.name in skipped_names:
            continue
        relative_path = source_file.relative_to(source_dir)
        destination_file = destination_dir / relative_path
        destination_file.parent.mkdir(parents=True, exist_ok=True)
        if source_file.name in TEMPLATED_FILES:
            content = string.Template(source_file.read_text()).safe_substitute(substitutions)
            destination_file.write_text(content)
        else:
            shutil.copy2(source_file, destination_file)
        log.info(f"Created {destination_file}")


@click.group()
def docs() -> None:
    """Documentation website commands."""


@docs.command(name="scaffold")
@click.option(
    "--project-title",
    "-t",
    required=True,
    help="Human-readable title shown in the navbar and homepage (e.g., `My Domain Model`).",
)
@click.option(
    "--project-name",
    "-p",
    required=True,
    help="Machine-readable project name (i.e., repo slug) (e.g., `my-domain-model`).",
)
@click.option("--org-name", "-o", required=True, help="GitHub organization name (e.g., `myorg`).")
@click.option(
    "--pages-url", "-u", required=True, help="Full deployed URL (e.g., `https://myorg.github.io/my-domain-model`)."
)
@click.option(
    "--github-repo-url",
    "-g",
    required=True,
    help="Full URL to the GitHub repository (e.g., `https://github.com/myorg/my-domain-model`).",
)
@click.option(
    "--output",
    default="website",
    show_default=True,
    type=click.Path(path_type=Path),
    help="Output directory path.",
)
@click.option("--force", is_flag=True, default=False, help="Overwrite the output directory if it already exists.")
def scaffold(
    project_title: str,
    project_name: str,
    org_name: str,
    pages_url: str,
    github_repo_url: str,
    output: Path,
    force: bool,
) -> None:
    """Scaffold a Docusaurus documentation website for an s2dm modeling project."""
    if output.exists():
        if not force:
            log.error(f"Output directory '{output}' already exists. Use --force to overwrite.")
            sys.exit(1)
        shutil.rmtree(output)

    # Docusaurus requires url (bare origin) and baseUrl (sub-path) to be separate.
    # e.g. https://myorg.github.io/my-model → url=https://myorg.github.io  baseUrl=/my-model/
    _parsed = urlparse(pages_url)
    pages_origin = f"{_parsed.scheme}://{_parsed.netloc}"
    pages_base_url = (_parsed.path.rstrip("/") + "/") if _parsed.path.strip("/") else "/"

    substitutions = {
        "project_title": project_title,
        "project_name": project_name,
        "org_name": org_name,
        "pages_origin": pages_origin,
        "pages_base_url": pages_base_url,
        "github_repo_url": github_repo_url,
    }

    copy_template_tree(TEMPLATE_DIR, output, substitutions)
    for source_dir, destination_name in ((INSIGHTS_UI_DIR, "insights-ui"), (LEDGER_UI_DIR, "ledger-ui")):
        copy_template_tree(
            source_dir,
            output / "src" / destination_name,
            substitutions,
            excluded_files=SHARED_UI_EXCLUDED_FILES,
        )

    log.success(
        f"Website scaffolded to '{output}/'.\n"
        f"  Next steps:\n"
        f"    cd {output}\n"
        f"    npm ci\n"
        f"    npm run doc   # generates introspection.json + GraphQL API docs\n"
        f"    npm start     # local preview at http://localhost:3000"
    )
