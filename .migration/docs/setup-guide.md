# S2DM Migration Workflow Setup Guide

This guide explains how to set up the automated S2DM migration workflow in your repository. The workflow automatically generates artifacts (GraphQL schemas, JSON schemas, registry files, and SKOS RDF) when changes are made to your specification files.

## Prerequisites

- A clean repository with a `spec/` directory containing schema files written in `GraphQL SDL` and following the data modeling ruleset of the `S2DM` approach.
- GitHub Actions enabled in your repository. For more information, follow this [guide](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository).

> !NOTE If the repository is empty, or if the user is starting from scratch without any schema files, then the tools will create an empty `spec/` directory.

## Setup Steps

### 1. Copy Files from S2DM Repository

The migration workflow comprises two files: `migrate.yml` and `.bumpversion.toml`.

The `migrate.yml` defines a GitHub Actions workflow that is responsible for exporting new releases based on changes to the GraphQL specification of the domain data model repository. The workflow is explained [here](#how-the-workflow-works). The `.bumpversion.toml` is utilized to track the versions of the created releases. Users of the automation should copy both files into the domain data model repository. This can be achieved through one of the following methods:

#### Option A: Using the setup script (recommended)

Run the automated setup script that handles everything for you:

```bash
curl -fsSL https://raw.githubusercontent.com/COVESA/s2dm/main/.migration/setup-repository.sh | bash

curl -fsSL https://raw.githubusercontent.com/COVESA/s2dm/main/.migration/setup-repository.sh | bash -s -- --directory /path/to/your/project
```

This script will:

- Initialize a git repository if needed
- Create the `spec/` directory
- Download the required workflow and configuration files
- Handle existing files with confirmation prompts

#### Option B: Download files directly from GitHub

1. Download the workflow file:
   - Go to https://github.com/COVESA/s2dm/blob/main/.migration/workflows/migrate.yml
   - Click "Raw" and save the file to `.github/workflows/migrate.yml` in your repository

2. Download the version bump configuration:
   - Go to https://github.com/COVESA/s2dm/blob/main/.migration/.bumpversion.toml
   - Click "Raw" and save the file to `.bumpversion.toml` at your repository root

#### Option C: Using Git (if you have both repositories locally)

```bash
cp path/to/s2dm/.migration/workflows/migrate.yml .github/workflows/migrate.yml
cp path/to/s2dm/.migration/.bumpversion.toml .bumpversion.toml
```

#### Option D: Using curl

```bash
mkdir -p .github/workflows

curl -o .github/workflows/migrate.yml https://raw.githubusercontent.com/COVESA/s2dm/main/.migration/workflows/migrate.yml

curl -o .bumpversion.toml https://raw.githubusercontent.com/COVESA/s2dm/main/.migration/.bumpversion.toml
```

Ensure your repository has the following structure:

```plain
your-repo/
├── .github/
│   └── workflows/
│       └── migrate.yml          # Copied from COVESA/s2dm
├── .bumpversion.toml            # Copied from COVESA/s2dm
├── spec/                        # Your specification files (GraphQL)
│   └── ...
└── README.md
```

### 2. Configure Repository Variables

The workflow supports optional configuration for the `s2dm` commands through GitHub repository variables.

Go to your repository → Settings → Secrets and variables → Actions → Variables tab, and add:

#### SKOS Generation Variables

- **`SKOS_NAMESPACE`**: The namespace URI for SKOS concepts (e.g., `https://example.org/vss#`)
- **`SKOS_PREFIX`**: The prefix for SKOS concept URIs (e.g., `ns`)
- **`SKOS_LANGUAGE`**: BCP 47 language tag for SKOS labels (default: `en`)

#### Registry Variables

- **`CONCEPT_NAMESPACE`**: The namespace URI for concept URIs (e.g., `https://example.org/vss#`)
- **`CONCEPT_PREFIX`**: The prefix for concept URIs (e.g., `ns`)

#### SHACL Generation Variables

- **`SHACL_SERIALIZATION_FORMAT`**: RDF serialization format (default: `ttl`)
- **`SHACL_SHAPES_NAMESPACE`**: Namespace for SHACL shapes (e.g., `http://example.ns/shapes#`)
- **`SHACL_SHAPES_PREFIX`**: Prefix for SHACL shapes (e.g., `shapes`)
- **`SHACL_MODEL_NAMESPACE`**: Namespace for data model (e.g., `https://example.ns/model#`)
- **`SHACL_MODEL_PREFIX`**: Prefix for data model (e.g., `model`)

> Note: All variables are optional. If not set, the commands will use their default values.

## How the Workflow Works

The migration workflow is triggered on pushes to the `main` branch when files in the `spec/` directory are modified.

### Critical Workflow Steps

#### 1. Version Bump Detection

```yaml
- name: Check spec version bump
```

- Compares current spec with the previous release
- Determines if changes require a `major`, `minor`, `patch`, or no version bump
- Skips the entire workflow if no version bump is needed

#### 2. Unit Synchronization

```yaml
- name: Sync units
```

- Synchronizes unit definitions from the QUDT repository
- Runs before schema composition to provide up-to-date unit definitions

#### 3. Schema Composition

```yaml
- name: Compose GraphQL schema
```

- Composes a valid GraphQL SDL schema from:
  - All the specification files of your domain model located inside the `<your-repo>/spec/` directory.
  - All the used items from the [pre-defined elements in the `S2DM`](https://github.com/COVESA/s2dm/tree/main/src/s2dm/spec) repo.
- Output: `.artifacts/graphql/schema.graphql`

#### 4. JSON Schema Generation

```yaml
- name: Export JSON schema
```

- Exports a JSON schema from a GraphQL SDL schema
- Output: `.artifacts/jsonschema/schema.json`

#### 5. Registry Management

```yaml
- name: Initialize registry  # (first release only)
- name: Update registry      # (subsequent releases)
```

- **Initialize**: Creates the first registry with concept URIs and spec history
- **Update**: Updates existing registry with new concepts and tracks changes
- Output: `.artifacts/registry/history`

#### 6. SHACL Generation

```yaml
- name: Export SHACL
```

- Exports SHACL (Shapes Constraint Language) validation shapes from a GraphQL schema
- Output: `.artifacts/shacl/schema.shacl.ttl` (Turtle RDF format)

#### 7. SKOS RDF Generation

```yaml
- name: Generate SKOS RDF
```

- Parses the reference specification (in GraphQL SDL) and generates a set of RDF triples that use the `SKOS` vocabulary, which enables the arbitrary extension of a vocabulary in a decoupled manner.
- Output: `.artifacts/skos/schema.ttl` (Turtle RDF format)

#### 8. VSpec Generation

```yaml
- name: Export vspec
```

- Exports the GraphQL schema in the Vehicle Signal Specification (`.vspec`) format.
- Output: `.artifacts/vspec/schema.vspec`

#### 9. Release Creation

```yaml
- name: Bump version and push tags
- name: Create release
```

- Automatically bumps version using `bump-my-version`
- Creates and pushes version tags (e.g., `v1.2.3`)
- Creates a GitHub release with all generated artifacts

## Workflow Triggers

The workflow runs when:

- Code is pushed to the `main` branch
- Files in the `spec/` directory are modified
- The spec version check determines a version bump is needed

## Generated Artifacts

Each successful run produces:

- **GraphQL Schema**: `schema.graphql` - Combined GraphQL schema
- **JSON Schema**: `schema.json` - JSON Schema representation
- **Registry**: `history` - Concept registry with version history
- **SHACL Shapes**: `schema.ttl` - Validation shapes in Turtle format
- **SKOS RDF**: `schema.ttl` - Semantic vocabulary in Turtle format
- **VSpec**: `schema.vspec` - Vehicle Signal Specification format
