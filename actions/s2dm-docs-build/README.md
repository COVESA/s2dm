# S2DM Docs Build Action

GitHub Action for building and deploying a Docusaurus documentation site for an s2dm modeling project.

## Features

- Composes GraphQL schema files into a single `dist/model.graphql`
- Scaffolds a Docusaurus 3 website via `s2dm docs scaffold` (no website files need to be checked into your repository)
- Generates GraphQL API reference docs from a live introspection
- Builds and deploys the site to GitHub Pages

## Why a composite action instead of the reusable workflow?

This action is the composite-action counterpart to the reusable workflow at
[`.github/workflows/docs-build.yml`](../../.github/workflows/docs-build.yml). Reusable workflows
(`jobs.<id>.uses: owner/repo/.github/workflows/x.yml@ref`) can only be called from repositories on
the **same GitHub product/instance** as the caller — there is no cross-instance resolution, even
with GitHub Connect enabled. Composite actions (`uses: owner/repo/path@ref`) don't have that
restriction: GitHub Enterprise Server instances can resolve them from github.com via GitHub
Connect's "automatic access to GitHub.com actions" setting.

Use this action instead of the reusable workflow when your repository lives on a GitHub Enterprise
Server instance. Otherwise, the reusable workflow remains the simpler option for github.com-native
adopters.

## Usage

Unlike a reusable workflow, a composite action runs as steps inside the caller's own job, so
`permissions` and the deployment `environment` must be declared on the caller's job (they cannot be
set by the action itself):

```yaml
name: Docs
on:
  push:
    branches:
      - main
    paths:
      - 'spec/**'
  workflow_dispatch:

permissions:
  pages: write
  id-token: write

jobs:
  docs:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.docs-build.outputs.page-url }}
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Build and deploy docs
        id: docs-build
        uses: COVESA/s2dm/actions/s2dm-docs-build@main
        with:
          project-title: "My Domain Model"
          project-name: my-model
          org-name: myorg
          pages-url: https://myorg.github.io/my-model
          github-repo-url: https://github.com/myorg/my-model
          schema-sources: "spec"
```

### Multiple schema sources

`schema-sources` is a space-separated list of directories or files passed to `s2dm compose -s`.
Each token becomes one `-s` flag:

```yaml
with:
  schema-sources: "spec/core spec/extensions/seat.graphql"
```

### Pinning the s2dm version

```yaml
with:
  s2dm-version: "0.22.0"
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `project-title` | Human-readable project title shown in the navbar and homepage | Yes | - |
| `project-name` | Machine-readable project name used as the repo slug | Yes | - |
| `org-name` | GitHub organization name | Yes | - |
| `pages-url` | Full URL where the site is deployed (e.g. `https://myorg.github.io/my-model`) | Yes | - |
| `github-repo-url` | Full URL to the GitHub repository | Yes | - |
| `schema-sources` | Space-separated paths/dirs passed to `s2dm compose -s` | Yes | - |
| `s2dm-version` | s2dm version to install (e.g. `0.22.0`). Omit to use the latest release | No | `''` |

## Outputs

| Output | Description |
|--------|-------------|
| `page-url` | The URL of the deployed GitHub Pages site |

## Requirements

- GitHub Pages enabled for the repository, with the source set to "GitHub Actions"
- `permissions: pages: write` and `permissions: id-token: write` declared on the calling job
- A `github-pages` deployment environment (created automatically by GitHub Pages on first deploy)

## How It Works

1. Installs Python, `uv`, and the `s2dm` CLI
2. Composes the adopter's GraphQL schema files into `dist/model.graphql`
3. Scaffolds a fresh Docusaurus website into `./website` via `s2dm docs scaffold`
4. Installs Node dependencies and generates the GraphQL API reference (`npm run doc`)
5. Builds the site (`npm run build`)
6. Uploads and deploys the built site to GitHub Pages
