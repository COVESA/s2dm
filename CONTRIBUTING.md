# Contributing

Contributions to the [S2DM repository](https://github.com/covesa/s2dm) are welcome.
> [!NOTE]
> This guide is for contributions to the `S2DM` approach itself.
> If you want to contribute to a certain data specification of a particular domain that follows the `S2DM` approach, then refer to the project, team, or organization that hosts the specification files.

## Process

- Verify whether your concern or feature request is already covered in the documented [issues](https://github.com/covesa/s2dm/issues) or [discussions](https://github.com/covesa/s2dm/discussions). If not, then create one.
- Propose a solution to the documented issue by commenting the intention.
- Work on it and create a pull request.

## Development Environment

`S2DM` uses [uv](https://docs.astral.sh/uv/) for packaging and
dependency management.
To start developing with `S2DM`, install `uv`
using the [recommended method](https://docs.astral.sh/uv/#getting-started).

Once `uv` is installed, install the dependencies with the following command:

```shell
uv sync
```

It will create a virtual environment `.venv` in the root of the project.
You can run things in the virtual environment by using a `uv run` prefix for commands, e.g.:

```shell
uv run <some-command>
```

> [!TIP]
> You can run things without typing everytime `uv run` by activating the virtual environment:
>
> ```shell
> source .venv/bin/activate
> ```
>
> To deactivate the virtual environment simply run:
>
> ```shell
> deactivate
> ```

The rest of this document assumes you are in the virtual environment by either activating or prefixing commands with `uv run`.

### Pre-Commit-Hooks

Pre commit hooks can be setup with:

```bash
pre-commit install
```

### Tests

Run tests with the following command:

```bash
pytest --cov-report term-missing --cov=s2dm -vv
```

New code should ideally have tests and not break existing tests.

### Type Checking

Simplified Semantic Data Modeling uses type annotations throughout, and `mypy` to do the checking. Run the following to type check Simplified Semantic Data Modeling:

```bash
mypy --ignore-missing-imports --no-implicit-optional --warn-unreachable
```

### Code Formatting

Simplified Semantic Data Modeling uses [`ruff`](https://docs.astral.sh/ruff/) for code formatting.
Since it is very fast it makes sense to setup your editor to format on save.

Use `ruff format` to format all files in the current directory

### Versioning

This project uses **semantic versioning** with an automated release pipeline that analyzes commit messages following the [Conventional Commits](https://www.conventionalcommits.org/) specification.

#### Conventional Commits Implementation

Our versioning system automatically determines the appropriate version bump based on commit message patterns:

- **Patch releases** (e.g., 0.1.1 → 0.1.2): Triggered by commits starting with `fix:` or `perf:`
- **Minor releases** (e.g., 0.1.0 → 0.2.0): Triggered by commits starting with `feat:`
- **Major releases** (e.g., 0.1.0 → 1.0.0): Triggered by commits with breaking changes:
  - Commits with `!` after the type (e.g., `feat!:` or `fix!:`)
  - Commits containing `BREAKING CHANGE:` in the body

#### Zero-Based Versioning

Currently, we use **zero-based versioning** (0.x.y series) for pre-1.0 development:

- Breaking changes bump the **minor** version instead of major (0.1.0 → 0.2.0)
- This is controlled by the `ZERO_BASED_VERSIONING: true` environment variable in `.github/workflows/release.yml`
- When ready for stable releases, set this to `false` to switch to standard semantic versioning

#### Release Automation

The release process is fully automated through GitHub Actions (`.github/workflows/release.yml`):

1. **Commit Analysis**: Scans all commits since the last tag to determine version bump type
2. **Version Bumping**: Uses [bump-my-version](https://github.com/callowayproject/bump-my-version) to update version files
3. **Changelog Generation**: Uses [git-cliff](https://github.com/orhun/git-cliff) to generate structured changelogs
4. **Tagging**: Creates annotated Git tags with the new version
5. **GitHub Releases**: Automatically creates GitHub releases with changelog notes

#### Commit Message Enforcement

We use [**gitlint**](https://github.com/jorisroovers/gitlint) to enforce conventional commit message standards:

- **Configuration**: See `.gitlint` for rules and settings
- **Rules Enabled**:
  - `contrib-title-conventional-commits` - Enforces conventional commit format
  - Custom title length limits (5-100 characters)
  - Ignores GitHub Actions bot commits

#### Commit Message Format

Follow this format for all commits:

```txt
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Common types:**

- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

**Breaking changes:**

- Add `!` after type: `feat!: remove deprecated API`
- Or include `BREAKING CHANGE:` in footer

**Examples:**

```txt
# feature for exporters
feat(exporters): add jsonschema exporter

# fix in graphql processing
fix: resolve memory leak in graphql processing

# feature including breaking change
feat!: migrate to new configuration format

# breaking change in body
BREAKING CHANGE: configuration file structure has changed
```
