---
title: Contributing Guide
weight: 20
chapter: false
---

## Contributing to Simplified Semantic Data Modeling
> **NOTE:** This document explains how to contribute to the data modeling approach itself.
If you want to contribute to a certain data specification of a particular domain, then follow the [Modeling Guide](/guides/modeling/) instead.


## Development Environment

`S2DM` uses [uv](https://docs.astral.sh/uv/) for packaging and
dependency management. To start developing with `S2DM`, install `uv`
using the [recommended method](https://docs.astral.sh/uv/#getting-started).

Once `uv` is installed, install the dependencies with the following command:

```
uv sync
```

It will create a `.venv` in the root of the project.

If you want to have a shell in the virtual environment you can activate it with (for Linux/MacOS):

```
. .venv/bin/activate
```

The package is linked in editable mode so you will not need to reinstall the package when changing something.

Alternatively you can run things in the virtual environment by using a `uv run` prefix for commands, e.g.:

```
uv run pytest
```

**The following section commands assume you are in the virtual environment by either activating or prefixing commands with `uv run`!**

### Pre-Commit-Hooks

Pre commit hooks can be setup with:

```
pre-commit install
```

### Tests

Run tests with the following command:

```
pytest --cov-report term-missing --cov=s2dm -vv
```

New code should ideally have tests and not break existing tests.

### Type Checking

Simplified Semantic Data Modeling uses type annotations throughout, and `mypy` to do the checking. Run the following to type check Simplified Semantic Data Modeling:

```
mypy --ignore-missing-imports --no-implicit-optional --warn-unreachable
```

### Code Formatting

Simplified Semantic Data Modeling uses [`ruff`](https://docs.astral.sh/ruff/) for code formatting.
Since it is very fast it makes sense to setup your editor to format on save.

Use `ruff format` to format all files in the currenct directory

### Versioning

- This tool is using [semantic versioning](https://semver.org/spec/v2.0.0.html). [CHANGELOG.md](./CHANGELOG.md) should be updated on every source code change.
- A new version can be bumped with the support of [bump-my-version](https://github.com/callowayproject/bump-my-version), which is a `dev` dependency:
  ```bash
  # major,minor,patch
  bump-my-version bump minor
  ```
