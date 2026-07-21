# docs-website template

This directory is a Docusaurus 3 website template used by the `s2dm docs scaffold` command.
Running `s2dm docs scaffold` copies these files into a target directory (default: `website/`)
and substitutes project-specific placeholders in the files that contain them.

## Placeholder substitution

Two files contain `$variable` placeholders (Python `string.Template` syntax):

| File | Placeholders |
|---|---|
| `docusaurus.config.ts` | `$project_title`, `$pages_url`, `$org_name`, `$project_name`, `$github_repo_url` |
| `package.json` | `$project_name` |

All other files are copied verbatim.

## File inventory

| File | Purpose |
|---|---|
| `docusaurus.config.ts` | Site configuration: URL, navbar, plugins, Mermaid, GraphQL Markdown |
| `sidebars.ts` | Sidebar structure: Types, Enums, Scalars, Queries, Directives |
| `tsconfig.json` | TypeScript configuration for the Docusaurus project |
| `package.json` | Dependencies and scripts (`doc`, `build`, `start`) |
| `custom-mdx.cjs` | GraphQL Markdown formatter hook — injects Mermaid `classDiagram` into every Object type page |
| `scripts/generate-introspection.js` | Reads `../dist/model.graphql` and writes `static/introspection.json` for the Voyager visualizer |
| `src/pages/index.tsx` | Homepage: project title (from config), s2dm/COVESA links, Docs + Visualizer buttons |
| `src/pages/index.module.css` | Homepage layout styles |
| `src/pages/visualizer.tsx` | Voyager page — wraps `static/voyager.html` in a full-height iframe |
| `src/css/custom.css` | Global CSS overrides (light-only color mode) |
| `static/voyager.html` | Self-contained Voyager HTML — loads library from CDN, fetches `introspection.json` via baseUrl-relative path |
| `static/.nojekyll` | Prevents GitHub Pages from running Jekyll on the build output |
| `static/img/` | Default images: `favicon.ico` (site icon), `docusaurus-social-card.jpg` (OG image referenced by name in config) |
| `docs/.gitkeep` | Ensures `docs/` exists in a fresh git checkout; Docusaurus requires it before `graphql-to-doc` runs |
| `.gitignore` | Excludes generated outputs: `docs/api/`, `static/introspection.json`, `build/`, `node_modules/` |

## How it integrates with an s2dm project

The website expects the stand-alone composed schema (e.g., produced by `s2dm compose`) at `../dist/model.graphql` relative to the `website/` directory.
Make sure you generate it before starting the docusaurus website.

## Using it as GitHub page

To deploy this website to GitHub Pages, configure the following in your repository before running `s2dm docs scaffold`:

### 1. Enable GitHub Pages in your repository

Go to **Settings → Pages → Source** and select **GitHub Actions**.

### 2. Collect the required parameters

| Flag | Where to find it | Example |
|---|---|---|
| `--project-title` (`-t`) | Any human-readable name for the site | `"My Domain Model"` |
| `--project-name` (`-p`) | The GitHub repository name (slug) | `my-domain-model` |
| `--org-name` (`-o`) | The GitHub organization or user name | `myorg` |
| `--pages-url` (`-u`) | For standard GitHub Pages: `https://<org-name>.github.io/<project-name>`. Use your custom domain if one is configured. | `https://myorg.github.io/seat-model` |
| `--github-repo-url` (`-g`) | Full URL to the repository on GitHub | `https://github.com/myorg/my-domain-model` |

> After the creation of the website template files, the repository information can be reworked in the file XXX. Alternatively, the `s2dm docs scaffold` can be run again with the desired information and with the `--force` flag to overwrite the directory.



### 3. Run the scaffold command

```bash
s2dm docs scaffold \
  -t "Vehicle Seat Model" \
  -p seat-model \
  -o myorg \
  -u https://myorg.github.io/seat-model \
  -g https://github.com/myorg/seat-model
```

This creates a `website/` directory ready to be committed and deployed.

### 4. Deploy automatically via GitHub Actions

Instead of checking in the generated files, you can use the reusable workflow hosted in s2dm.
Add `.github/workflows/docs.yml` to your repo with:

```yaml
on:
  push:
    branches: [main]
    paths: ["spec/**"]  # adjust to your schema directory
  workflow_dispatch:

permissions:
  pages: write
  id-token: write

jobs:
  docs:
    uses: COVESA/s2dm/.github/workflows/docs-build.yml@main
    with:
      project_title: "Vehicle Seat Model"
      project_name: seat-model
      org_name: myorg
      pages_url: https://myorg.github.io/seat-model
      github_repo_url: https://github.com/myorg/seat-model
      schema_sources: "spec"  # space-separated dirs/files passed to s2dm compose -s
```

With this approach, no website files need to be committed to your repository.
