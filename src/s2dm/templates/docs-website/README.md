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
| `docusaurus.config.ts` | Site configuration: URL, navbar, plugins, Mermaid, GraphQL Markdown, and the plugin that gives Insights, Ledger and Releases a route per sidebar link |
| `sidebars.ts` | Sidebar structure: docs, plus the Insights, Ledger and Releases sidebars |
| `tsconfig.json` | TypeScript configuration for the Docusaurus project |
| `package.json` | Dependencies and scripts (`doc`, `build`, `start`) |
| `custom-mdx.cjs` | GraphQL Markdown formatter hook — injects Mermaid `classDiagram` into every Object type page |
| `scripts/generate-introspection.js` | Reads `../dist/model.graphql` and writes `static/introspection.json` for the Voyager visualizer |
| `scripts/copy-ledger.js` | Copies `../dist/ledger.db` to `static/ledger.db`, and removes a stale copy when no ledger is staged |
| `scripts/copy-sql-wasm.js` | Copies the installed sql.js WebAssembly binary to `static/sql-wasm.wasm` on `postinstall`, so it matches the installed version |
| `scripts/stage-releases.js` | Downloads the schemas of the latest releases with `gh` into `static/releases/` for the Releases page |
| `src/pages/index.tsx` | Homepage: project title (from config), s2dm/COVESA links, Docs + Visualizer + Insights + Ledger buttons |
| `src/pages/index.module.css` | Homepage layout styles |
| `src/pages/visualizer.tsx` | Voyager page — wraps `static/voyager.html` in a full-height iframe |
| `src/insights/` | Insights host page: the shared views inside the docs layout and sidebar |
| `src/ledger/` | Ledger host page: the shared views inside the docs layout and sidebar |
| `src/releases/` | Releases page: the schema of the selected release in a read-only editor |
| `src/insights-ui/` | Copied from `templates/insights-ui`; reached through the `@insights-ui` alias |
| `src/ledger-ui/` | Copied from `templates/ledger-ui`; reached through the `@ledger-ui` alias |
| `src/components/`, `src/store/`, `src/hooks/`, `src/utils/` | Host primitives the shared trees import through `@/` |
| `src/css/custom.css` | Global CSS overrides, Tailwind sources, and the rules the shared components need that Docusaurus does not supply |
| `static/voyager.html` | Self-contained Voyager HTML — loads library from CDN, fetches `introspection.json` via baseUrl-relative path |
| `static/.nojekyll` | Prevents GitHub Pages from running Jekyll on the build output |
| `static/img/` | Default images: `favicon.ico` (site icon), `docusaurus-social-card.jpg` (OG image referenced by name in config) |
| `docs/.gitkeep` | Ensures `docs/` exists in a fresh git checkout; Docusaurus requires it before `graphql-to-doc` runs |
| `.gitignore` | Excludes generated outputs: `docs/api/`, `static/introspection.json`, `static/insights.json`, `static/sql-wasm.wasm`, `static/ledger.db`, `static/releases/`, `build/`, `node_modules/` |

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

1. Stage the database at `../dist/ledger.db`, beside the composed schema. The
   `export sqlite` command of [ModL](https://github.com/COVESA/modl) makes it from a
   ledger directory:

   ```sh
   modl export --ledger-dir <ledger directory> --output ../dist/ledger.db sqlite
   ```

   The command stops when the file already exists. `--overwrite` after `sqlite`
   replaces it.
2. `npm run doc` copies it to `static/ledger.db`.
3. The page fetches that file at a base-URL-aware path and opens it with sql.js,
   using the `static/sql-wasm.wasm` binary staged on `npm install`.

The database is opened and queried on a Web Worker, so a slow query leaves the
page responsive. A query that is cancelled, or that passes the deadline, ends
that worker; the ledger is reopened behind it from the bytes already fetched.

The ledger is optional. With nothing staged, `copy-ledger.js` removes any stale copy and
the Ledger page says that no ledger is available and shows no sidebar. The rest of the site is
unaffected.

### Releases

The Releases page shows the schemas of past releases in a read-only editor. Browsers
cannot read GitHub release files, so the build downloads them:

```sh
GH_REPO=github.com/<org>/<repo> node scripts/stage-releases.js 5
```

The script needs the GitHub CLI (`gh`) with read access to the repository. An archive
release also needs `python3` to extract the archive.

The argument is the number of releases to stage, a whole number from 1 to 50. The script
goes through the published releases from newest to oldest. It leaves out drafts and
pre-releases. It stages the schema from the first of these assets that a release has:

1. `schema.graphql`, with a `metadata.yaml` asset next to it.
2. `release.tar.gz`.
3. The only archive of the release (`.tar`, `.tar.gz`, `.tgz` or `.zip`).

An archive needs `metadata.yaml` at its top and exactly one `schema.graphql`. A release
that fails, or whose tag has a `/`, is skipped with a warning and does not count toward
the limit.

The script clears `static/releases/` first. It then writes each schema to
`static/releases/<tag>/schema.graphql` and the tags, newest first, to
`static/releases/releases.json`. The newest release is at `/releases`, the others at
`/releases/<tag>`. With no releases staged, the Releases page says that no releases are
available and shows no sidebar.

Run `npm run test:releases` to test the script.

## GraphQL-Markdown performance patch

`npm ci` and `npm install` apply the versioned patch in `patches/` through
`patch-package --error-on-fail`. The printer dependency is pinned to `1.19.2`
in `package.json` so an upgrade cannot silently change the patch target.

The patch reuses the schema map when printing relation sections. Without it,
the printer rebuilds the full map three times per type page. Maps are keyed by
schema object and reset on each `Printer.init()` call. The schema must remain
unchanged while its pages are generated; formatter hooks should change output,
not the schema.

Run `npm run test:patch` to check relation output, schema isolation, and cache
reset. This test is explicit and does not run during normal documentation builds.
When upgrading GraphQL-Markdown, review the patch, run this test, and compare
the generated pages. Remove the patch and its install hook once an upstream
release includes an equivalent fix.

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
  contents: read
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
      releases_limit: 5  # optional; releases on the Releases page, at most 50 (default 10, 0 for none)
```

With this approach, no website files need to be committed to your repository.
