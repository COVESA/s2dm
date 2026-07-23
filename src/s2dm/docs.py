import shutil
import string
import sys
from pathlib import Path
from urllib.parse import urlparse

import rich_click as click

from s2dm import log

TEMPLATE_DIR = Path(__file__).parent / "templates" / "docs-website"

TEMPLATED_FILES = {"docusaurus.config.ts", "package.json"}


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

    for src_file in sorted(TEMPLATE_DIR.rglob("*")):
        if src_file.is_dir() or "node_modules" in src_file.parts:
            continue
        rel = src_file.relative_to(TEMPLATE_DIR)
        dst_file = output / rel
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        if src_file.name in TEMPLATED_FILES:
            content = string.Template(src_file.read_text()).safe_substitute(substitutions)
            dst_file.write_text(content)
        else:
            shutil.copy2(src_file, dst_file)
        log.info(f"Created {dst_file}")

    log.success(
        f"Website scaffolded to '{output}/'.\n"
        f"  Next steps:\n"
        f"    cd {output}\n"
        f"    npm ci\n"
        f"    npm run doc   # generates introspection.json + GraphQL API docs\n"
        f"    npm start     # local preview at http://localhost:3000"
    )
