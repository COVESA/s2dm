# S2DM Publish Action

GitHub Action for automated artifact generation and publishing workflow through S2DM.

## Features

- Automatic version bump detection
- Registry management (init/update)
- GraphQL schema composition
- JSON schema generation
- SHACL generation
- SKOS RDF generation
- Schema RDF generation (sorted n-triples and Turtle)
- VSpec generation
- Automated release creation

## Usage

### Basic Example

```yaml
name: Publish
on:
  push:
    branches:
      - main
    paths:
      - 'spec/**'

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Run S2DM publish
        uses: COVESA/s2dm/actions/s2dm-publish@main
        with:
          repository-path: .
          spec-path: ./spec
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

### Advanced Example with All Options

```yaml
name: Publish
on:
  push:
    branches: [main]
    paths: ['spec/**']

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Run S2DM publish
        uses: COVESA/s2dm/actions/s2dm-publish@main
        with:
          repository-path: .
          spec-path: ./spec
          github-token: ${{ secrets.GITHUB_TOKEN }}
          s2dm-path: s2dm
          concept-namespace: 'https://example.com/concepts/'
          concept-prefix: 'ex'
          shacl-serialization-format: 'turtle'
          shacl-shapes-namespace: 'https://example.com/shapes/'
          shacl-shapes-prefix: 'sh'
          shacl-model-namespace: 'https://example.com/model/'
          shacl-model-prefix: 'model'
          skos-namespace: 'https://example.com/skos/'
          skos-prefix: 'skos'
          skos-language: 'en'
          schema-rdf-namespace: 'https://example.com/ontology#'
          schema-rdf-prefix: 'ns'
          schema-rdf-language: 'en'
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `repository-path` | Path to the git repository root | Yes | - |
| `spec-path` | Path to the spec directory relative to the root of the repository | No | `./spec` |
| `github-token` | GitHub token for creating releases | Yes | - |
| `s2dm-path` | Path where S2DM repository will be checked out | No | `s2dm` |
| `concept-namespace` | Concept namespace for registry | No | `''` |
| `concept-prefix` | Concept prefix for registry | No | `''` |
| `shacl-serialization-format` | SHACL serialization format | No | `''` |
| `shacl-shapes-namespace` | SHACL shapes namespace | No | `''` |
| `shacl-shapes-prefix` | SHACL shapes prefix | No | `''` |
| `shacl-model-namespace` | SHACL model namespace | No | `''` |
| `shacl-model-prefix` | SHACL model prefix | No | `''` |
| `skos-namespace` | SKOS namespace | No | `''` |
| `skos-prefix` | SKOS prefix | No | `''` |
| `skos-language` | SKOS language | No | `''` |
| `schema-rdf-namespace` | Namespace URI for schema-rdf (e.g. `https://example.com/ontology#`). If provided, generates schema.nt and schema.ttl. | No | `''` |
| `schema-rdf-prefix` | Prefix for schema-rdf concept URIs | No | `ns` |
| `schema-rdf-language` | BCP 47 language tag for schema-rdf prefLabels | No | `en` |

## Outputs

| Output | Description |
|--------|-------------|
| `version-bump` | Type of version bump (major, minor, patch, none) |
| `latest-tag` | The latest git tag after release |
| `continue` | Whether publishing should continue |

## Authentication

### For Creating Releases

The action requires a `github-token` to create releases in your repository. You can use the default `GITHUB_TOKEN` provided by GitHub Actions:

```yaml
- name: Run S2DM publish
  uses: COVESA/s2dm/actions/s2dm-publish@main
  with:
    repository-path: .
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

### For Pushing to Your Repository

The action pushes version bumps and tags to your repository. When you checkout your repository **before** calling the action, you must use credentials with push permissions:

**For unprotected branches:**

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  # Default GITHUB_TOKEN is sufficient
```

**For protected branches with push restrictions:**

You need to use credentials that can bypass branch protection:

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    token: ${{ secrets.PAT_TOKEN }}  # Token with bypass permissions
    # OR
    ssh-key: ${{ secrets.DEPLOY_KEY }}  # Deploy key with bypass permissions
```

## Requirements

Your repository must have:

1. A `spec/` directory with S2DM specification files
2. A `.bumpversion.toml` configuration file for version management
3. Proper permissions: `contents: write` in the workflow

### Example `.bumpversion.toml`

```toml
[tool.bumpversion]
 current_version = "0.0.0"
 parse = "(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)"
 serialize = ["{major}.{minor}.{patch}"]
 search = "{current_version}"
 replace = "{new_version}"
 regex = false
 ignore_missing_version = false
 ignore_missing_files = false
 tag = true
 sign_tags = false
 tag_name = "v{new_version}"
 tag_message = "Bump version: {current_version} → {new_version}"
 allow_dirty = false
 commit = true
 message = "chore: bump version {current_version} → {new_version}"
 moveable_tags = []
 commit_args = ""
```

## Registry and Variant IDs

The action automatically manages variant-based IDs for schema concepts:

- **Variant IDs**: Each concept gets a semantic version (e.g., `Vehicle.speed/v1.0`)
- **Change Detection**: GraphQL Inspector detects schema changes and triggers version increments
- **Breaking vs Non-Breaking**: Breaking changes increment major version (v1.0 → v2.0), non-breaking changes increment minor (v1.0 → v1.1)
- **History Tracking**: All concept definitions are saved to a history directory for traceability

### Release Artifacts

Each release includes:
- `registry.json` - Complete spec history with variant IDs
- `variant_ids_<tag>.json` - Current variant ID mappings
- `concept_uris_<tag>.json` - Concept URI definitions
- `history/` - Directory with historical concept definitions

## How It Works

1. **Validation**: Validates that the spec directory exists and contains at least one .graphql file
1. **Setup**: Checks out S2DM repository, installs Python 3.13, Node.js 20, uv, and S2DM dependencies
2. **Version Check**: Downloads previous release and compares current spec to determine version bump type
3. **GraphQL Diff Generation**: Uses `s2dm diff graphql` (powered by @graphql-inspector/core) to detect schema changes (for updates)
4. **Registry Management**:
   - For initial release: Initializes registry with variant IDs starting at v1.0
   - For updates: Increments variant IDs based on detected changes (major for breaking, minor for non-breaking)
5. **Artifact Generation**: Generates all required artifacts (GraphQL, JSON Schema, SHACL, SKOS, schema RDF, VSpec)
6. **Version Bump**: Updates version using bump-my-version and creates git tag
7. **Release Creation**: Creates GitHub release with all generated artifacts including:
   - Composed GraphQL schema
   - JSON Schema
   - SHACL shapes
   - SKOS RDF
   - Schema RDF (schema.nt, schema.ttl) when `schema-rdf-namespace` is provided
   - VSpec
   - Registry files (spec_history, variant_ids, concept_uris)
   - History directory with concept definitions
