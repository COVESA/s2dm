# S2DM Migration Workflow Setup Guide

This guide explains how to set up the automated S2DM publishing workflow in your repository. The workflow uses the `s2dm-publish` action to automatically generate artifacts when changes are made to your specification files.

## Prerequisites

- A clean repository with a `spec/` directory containing schema files written in `GraphQL SDL` and following the data modeling ruleset of the `S2DM` approach.
- GitHub Actions enabled in your repository. For more information, follow this [guide](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository).

> Note: If the repository is empty, or if the user is starting from scratch without any schema files, then the tool will create an empty `spec/` directory.

## Setup Steps

### 1. Copy Files from S2DM Repository

The publishing workflow comprises two files: `migrate.yml` and `.bumpversion.toml`.

The `migrate.yml` defines a GitHub Actions workflow that uses the `s2dm-publish` action to export new releases based on changes to the GraphQL specification of the domain data model repository. The workflow is explained [here](#how-the-workflow-works). The `.bumpversion.toml` is utilized to track the versions of the created releases. Users of the automation should copy both files into the domain data model repository. This can be achieved through one of the following methods:

#### Option A: Using the setup script **(recommended)**

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

The workflow supports optional configuration for the `s2dm-publish` action through GitHub repository variables.

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

### 3. Configure Deploy Key for Protected Branches (Optional)

If your `main` branch has protection rules that prevent the default `GITHUB_TOKEN` from pushing commits and tags, you need to configure a deploy key with write access.

#### Creating a Deploy Key

1. **Generate an SSH key pair** (available on Linux, macOS, and Windows 10+):

   ```bash
   ssh-keygen -t ed25519 -C "s2dm-publish-action" -f ~/.ssh/s2dm_deploy_key -N ""
   ```

   - `-t ed25519`: Use ED25519 algorithm
   - `-C "s2dm-publish-action"`: Add a comment to identify the key
   - `-f ~/.ssh/s2dm_deploy_key`: Output file path
   - `-N ""`: Empty passphrase (required for automated workflows)

   This creates two files:
   - `~/.ssh/s2dm_deploy_key` (private key)
   - `~/.ssh/s2dm_deploy_key.pub` (public key)

2. **Add the public key as a deploy key:**

   - Go to your repository → Settings → Deploy keys → Add deploy key
   - Title: `S2DM Publish Action`
   - Key: Paste the content of `~/.ssh/s2dm_deploy_key.pub`
   - **Enable "Allow write access"**
   - Click "Add key"

3. **Add the private key as a repository secret:**

   - Go to your repository → Settings → Secrets and variables → Actions → Secrets tab
   - Click "New repository secret"
   - Name: `DEPLOY_KEY`
   - Value: Paste the content of `~/.ssh/s2dm_deploy_key`
   - Click "Add secret"

4. **Configure branch protection to allow deploy key:**

   Choose one of the following based on your setup:

   **Option A: Using Rulesets** (recommended)
   - Go to Settings → Rules → Rulesets
   - Edit the ruleset that applies to your `main` branch (or create one)
   - Under "Bypass list", click "Add bypass"
   - Select "Deploy keys" from the list
   - Save the ruleset
   - See [GitHub Rulesets documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)

   **Option B: Using Classic Branch Protection Rules**
   - Go to Settings → Branches → Branch protection rules for `main`
   - Ensure "Do not allow bypassing the above settings" is **unchecked** to allow deploy keys (which have admin-level permissions) to push
   - See [Branch Protection Rules documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)

## How the Workflow Works

The workflow uses the `s2dm-publish` action which handles all the artifact generation and publishing steps. It runs when:

- Code is pushed to the `main` branch
- Files in the `spec/` directory are modified
- The spec version check determines a version bump is needed _(handled by the `s2dm-publish` action)_

For detailed information about the action's workflow steps, inputs, outputs, and how it works, see the [`s2dm-publish` action documentation](https://github.com/COVESA/s2dm/blob/main/actions/s2dm-publish/README.md)
