# docs-website template

This directory is a Docusaurus 3 website template used by the `s2dm docs scaffold` command.
Running `s2dm docs scaffold` copies these files into a target directory (default: `website/`)
and substitutes project-specific placeholders in the files that contain them.

## Placeholder substitution

Three files contain `$variable` placeholders (Python `string.Template` syntax):

| File | Placeholders |
|---|---|
| `docusaurus.config.ts` | `$project_title`, `$pages_origin`, `$pages_base_url`, `$org_name`, `$project_name`, `$github_repo_url` |
| `package.json` | `$project_name` |
| `package-lock.json` | `$project_name` |

`--pages-url` is split into `$pages_origin` (scheme and host) and `$pages_base_url` (path,
always with a trailing slash), which Docusaurus needs as separate settings.

All other files are copied verbatim.

## File inventory

| File | Purpose |
|---|---|
| `docusaurus.config.ts` | Site configuration: URL, navbar, plugins, Mermaid, GraphQL Markdown, and the plugin that gives Insights and Ledger a route per sidebar link |
| `sidebars.ts` | Sidebar structure: docs, plus the Insights and Ledger sidebars |
| `tsconfig.json` | TypeScript configuration for the Docusaurus project |
| `package.json` | Dependencies and scripts (`doc`, `build`, `start`) |
| `custom-mdx.cjs` | GraphQL Markdown formatter hook — injects Mermaid `classDiagram` into every Object type page |
| `scripts/generate-introspection.js` | Reads `../dist/model.graphql` and writes `static/introspection.json` for the Voyager visualizer |
| `scripts/copy-ledger.js` | Copies `../dist/ledger.db` to `static/ledger.db`, and removes a stale copy when no ledger is staged |
| `scripts/copy-sql-wasm.js` | Copies the installed sql.js WebAssembly binary to `static/sql-wasm.wasm` on `postinstall`, so it matches the installed version |
| `src/pages/index.tsx` | Homepage: project title (from config), s2dm/COVESA links, Docs + Visualizer + Insights + Ledger buttons |
| `src/pages/index.module.css` | Homepage layout styles |
| `src/pages/visualizer.tsx` | Voyager page — wraps `static/voyager.html` in a full-height iframe |
| `src/insights/` | Insights host page: the shared views inside the docs layout and sidebar |
| `src/ledger/` | Ledger host page: the shared views inside the docs layout and sidebar |
| `src/insights-ui/` | Copied from `templates/insights-ui`; reached through the `@insights-ui` alias |
| `src/ledger-ui/` | Copied from `templates/ledger-ui`; reached through the `@ledger-ui` alias |
| `src/components/`, `src/store/`, `src/hooks/`, `src/utils/` | Host primitives the shared trees import through `@/` |
| `src/css/custom.css` | Global CSS overrides, Tailwind sources, and the rules the shared components need that Docusaurus does not supply |
| `static/voyager.html` | Self-contained Voyager HTML — loads library from CDN, fetches `introspection.json` via baseUrl-relative path |
| `static/.nojekyll` | Prevents GitHub Pages from running Jekyll on the build output |
| `static/img/` | Default images: `favicon.ico` (site icon), `docusaurus-social-card.jpg` (OG image referenced by name in config) |
| `docs/.gitkeep` | Ensures `docs/` exists in a fresh git checkout; Docusaurus requires it before `graphql-to-doc` runs |
| `.gitignore` | Excludes generated outputs: `docs/api/`, `static/introspection.json`, `static/insights.json`, `static/sql-wasm.wasm`, `static/ledger.db`, `build/`, `node_modules/` |

## How it integrates with an s2dm project

The website expects the stand-alone composed schema (e.g., produced by `s2dm compose`) at `../dist/model.graphql` relative to the `website/` directory.
Make sure you generate it before starting the docusaurus website.

Running `npm run doc` generates the static artifacts before the API documentation:

- `static/introspection.json` for the visualizer
- `static/insights.json` for the Insights page
- `static/ledger.db` for the Ledger page, when a ledger was staged

### The ledger

The Ledger page reads a ModL ledger SQLite database in the browser, with no server.
The database reaches it the same way the schema does:

1. Stage the database at `../dist/ledger.db`, beside the composed schema.
2. `npm run doc` copies it to `static/ledger.db`.
3. The page fetches that file at a base-URL-aware path and opens it with sql.js,
   using the `static/sql-wasm.wasm` binary staged on `npm install`.

The database is opened and queried on a Web Worker, so a slow query leaves the
page responsive. A query that is cancelled, or that passes the deadline, ends
that worker; the ledger is reopened behind it from the bytes already fetched.

The ledger is optional. With nothing staged, `copy-ledger.js` removes any stale copy and
the page reports that it could not read a ledger. The rest of the site is unaffected.

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
      ledger_source: "spec/ledger.db"  # optional; omit if the model has no ledger
```

With this approach, no website files need to be committed to your repository.
