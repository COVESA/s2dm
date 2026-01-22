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

Pre-commit hooks can be set up with:

```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

The first command installs hooks that run before commits (code formatting, linting, type checking, etc.).
The second command installs the `commit-msg` hook that validates commit messages using gitlint.

Pre-commit hooks automatically run:
- **Ruff**: Code formatting and linting
- **Mypy**: Type checking on `src/` directory (uses your local virtual environment)
- **Various checks**: YAML, TOML, trailing whitespace, etc.
- **Gitlint**: Commit message validation (commit-msg stage)

> [!TIP]
> The mypy hook uses `language: system` with `uv run`, which means it uses your local virtual environment's dependencies. This is faster and avoids duplicating dependency lists.

> [!NOTE]
> Both hooks are required: the first validates your code, the second enforces conventional commit message standards as described in the [Commit Message Enforcement](#commit-message-enforcement) section.

### Tests

Run tests with the following command:

```bash
pytest --cov-report term-missing --cov=s2dm -vv
```

New code should ideally have tests and not break existing tests.

### Type Checking

Simplified Semantic Data Modeling uses type annotations throughout, and `mypy` to do the checking.

**Automatic checking:** Type checking runs automatically via pre-commit hooks when you commit changes to `src/`.

**Manual checking:** To manually type check the entire codebase:

```bash
mypy src/s2dm
# or with uv:
uv run mypy src/s2dm
```

The mypy configuration is defined in `pyproject.toml` under `[tool.mypy]` with `strict = true` mode enabled, which includes comprehensive type checking rules.

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

> [!TIP]
> **Recovering failed commit messages**: If gitlint rejects your commit, Git saves your message in `.git/COMMIT_EDITMSG`. Recover it with:
> ```bash
> git commit --edit --file=.git/COMMIT_EDITMSG
> ```
>
> Or create a convenient alias for quick recovery:
> ```bash
> git config --global alias.recommit 'commit -s --edit --file=.git/COMMIT_EDITMSG'
> # Then simply use: git recommit
> ```
>
> Test your message before committing:
> ```bash
> echo "feat: my feature" | gitlint
> ```

#### Commit Message Format

Follow this format for all commits:

```txt
<type>[optional scope]: <description>

[optional body]

Signed-off-by: Your Name <your.email@example.com>

[optional footer(s)]
```

**Important:** All commits must include a `Signed-off-by` line (Developer Certificate of Origin).

**Adding sign-off automatically:**

```bash
# Use -s flag when committing
git commit -s -m "feat: your message"

# Or configure git to always prompt for sign-off with an alias
git config alias.cs 'commit -s'

# Then use: git cs -m "feat: your message"
```

The `Signed-off-by` line certifies that you have the right to submit the code under the project's license.

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
# Feature for exporters
feat(exporters): add jsonschema exporter

This adds a new exporter that converts schemas to JSON Schema format.

Signed-off-by: John Doe <john.doe@example.com>

# Fix in graphql processing
fix: resolve memory leak in graphql processing

Signed-off-by: John Doe <john.doe@example.com>

# Feature including breaking change
feat!: migrate to new configuration format

The configuration file structure has been updated to YAML format.
Old TOML configs are no longer supported.

Signed-off-by: John Doe <john.doe@example.com>
```
