# S2DM Publish Action

GitHub Action for automated artifact generation and publishing workflow through S2DM.

## Features

- Automatic version bump detection
- Registry management (init/update)
- GraphQL schema composition
- JSON schema generation
- SHACL generation
- RDF export (SKOS concepts + ontology data graph)
- VSpec generation
- Release metadata generation
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
          metadata-path: metadata.yaml
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
          rdf-namespace: 'https://example.com/ontology#'
          rdf-prefix: 'ns'
          rdf-language: 'en'
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `repository-path` | Path to the git repository root | Yes | - |
| `spec-path` | Path to the spec directory relative to the root of the repository | No | `./spec` |
| `metadata-path` | Path to the repository metadata YAML file relative to the root of the repository | No | `metadata.yaml` |
| `github-token` | GitHub token for creating releases | Yes | - |
| `s2dm-path` | Path where S2DM repository will be checked out | No | `s2dm` |
| `concept-namespace` | Concept namespace for registry | No | `''` |
| `concept-prefix` | Concept prefix for registry | No | `''` |
| `shacl-serialization-format` | SHACL serialization format | No | `''` |
| `shacl-shapes-namespace` | SHACL shapes namespace | No | `''` |
| `shacl-shapes-prefix` | SHACL shapes prefix | No | `''` |
| `shacl-model-namespace` | SHACL model namespace | No | `''` |
| `shacl-model-prefix` | SHACL model prefix | No | `''` |
| `rdf-namespace` | Namespace URI for RDF export (e.g. `https://example.com/ontology#`). When provided, generates SKOS and data graph artifacts. | No | `''` |
| `rdf-prefix` | Prefix for RDF export concept URIs | No | `ns` |
| `rdf-language` | BCP 47 language tag for RDF export prefLabels | No | `en` |

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
2. A repository-level `metadata.yaml` file with `name`, `id`, and optional `preferred_prefix`
3. A `.bumpversion.toml` configuration file for version management
4. Proper permissions: `contents: write` in the workflow

### Example `metadata.yaml`

```yaml
name: VehicleModel
id: https://example.com/models/vehicle
preferred_prefix: vehicle
```

The action adds `version` from the release tag when generating release metadata. Do not include `version` in the repository metadata file.

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

- **Variant IDs**: Each concept gets a semantic version (e.g., `Vehicle.speed/v1.0`). When a namespace prefix is configured, IDs include the prefix (e.g., `ns:Vehicle.speed/v1.0`).
- **Change Detection**: GraphQL Inspector detects schema changes and triggers version increments
- **Breaking vs Non-Breaking**: Breaking changes increment major version (v1.0 → v2.0), non-breaking changes increment minor (v1.0 → v1.1)
- **History Tracking**: All concept definitions are saved to a history directory for traceability

### Release Artifacts

Each release includes:
- `metadata.yaml` - Release metadata with the release tag as `version`
- `registry.json` - Complete spec history with variant IDs
- `variant_ids_<tag>.json` - Current variant ID mappings
- `concept_uris_<tag>.json` - Concept URI definitions
- `history/` - Directory with historical concept definitions
- `rdf/skos.nt`, `rdf/skos.ttl` - SKOS concepts, collections, and labels
- `rdf/data_graph.nt`, `rdf/data_graph.ttl` - s2dm ontology instantiation

## How It Works

1. **Validation**: Validates that the spec directory exists and contains at least one .graphql file
1. **Setup**: Checks out S2DM repository, installs Python 3.13, Node.js 20, uv, and S2DM dependencies
2. **Version Check**: Downloads previous release and compares current spec to determine version bump type
3. **GraphQL Diff Generation**: Uses `s2dm diff graphql` (powered by @graphql-inspector/core) to detect schema changes (for updates)
4. **Registry Management**:
   - For initial release: Initializes registry with variant IDs starting at v1.0
   - For updates: Increments variant IDs based on detected changes (major for breaking, minor for non-breaking)
5. **Artifact Generation**: Generates all required artifacts (GraphQL, JSON Schema, SHACL, RDF, VSpec)
6. **Version Bump**: Updates version using bump-my-version and creates git tag
7. **Metadata Generation**: Copies repository metadata and adds the release tag as `version`
8. **Release Creation**: Creates GitHub release with all generated artifacts including:
   - Composed GraphQL schema
   - Release metadata
   - JSON Schema
   - SHACL shapes
   - RDF export (SKOS + data graph in .nt and .ttl formats) when `rdf-namespace` is provided
   - VSpec
   - Registry files (spec_history, variant_ids, concept_uris)
   - History directory with concept definitions
