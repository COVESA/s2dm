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
> ```shell
> source .venv/bin/activate
> ```
> To deactivate the virtual environment simply run:
> ```shell
> deactivate
> ```

The rest of this document assumes you are in the virtual environment by either activating or prefixing commands with `uv run`.

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

Use `ruff format` to format all files in the current directory

### Versioning
Under construction...
