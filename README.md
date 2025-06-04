# Simplified Semantic Data Modeling (S2DM)
Welcome to the **_Simplified Semantic Data Modeling (S2DM)_** repository.
`S2DM` is an approach for modeling data of multiple domains.
It is **_simple_** in the sense that any Subject Matter Expert (SME) could contribute to a controlled vocabulary with minimal data modeling expertise.
Likewise, it is **_semantic_** in the sense that it specifies meaningful data structures, their cross-domain relationships, and arbitrary classification schemes.

> **Disclaimer:** Bear in mind the word `Simplified` in the name.
This approach aims to foster the adoption of (some) good data modeling practices.
It does not intent to re invent, nor to replace long-standing standards, such as those of the [Semantic Web](https://www.w3.org/2001/sw/wiki/Main_Page).
Hence, this approach does not incorporate advanced reasoning capabilities or the use of comprehensive ontologies typically associated with traditional semantic data modeling.


`S2DM` adopts data modeling best practices and reuses the following elements:
- [GraphQL Schema Definition Language (SDL)](https://graphql.org/learn/schema/).
It provides a clear, human-readable syntax for defining data structures and relationships, making it easy for SMEs to understand and use without requiring deep technical expertise.
- [Simple Knowledge Organization System (SKOS)](https://www.w3.org/2004/02/skos/).
It offers a straightforward framework for creating and managing hierarchical classifications and relationships between concepts, facilitating the organization and retrieval of knowledge in a way that is both intuitive and semantically rich.

To learn more about the background that has led to S2DM, as well as its design principles, please read the [S2DM Approach Primer](docs/APPROACH_PRIMER.md).

> TODO: Add link to the rendered documentation of the project with GitHub

## Artifacts
`S2DM` consist of the following artifacts:
- [Data modeling guideline](docs/MODELING_GUIDE.md) - Instructions on how to model the data of a particular domain following the `S2DM` approach.
- [Tools](tools/README.md) - A collection of scripts and utilities to facilitate schema composition, management of identifiers, amoung other functions for a seamless usage of the `S2DM` approach.

## Repository Structure

- [docs/](docs/) - Documentation files.  
- [examples/](examples/) - Examples of the application of the `S2DM` approach.
- [src/](src/) - Source code for tools and utilities supporting the `S2DM` approach.

## Usage
The tools of this repository are a companion for the specification files that follow the `S2DM` approach.
If your domain is not modeled yet, simply refer to the [data modeling guideline](docs/MODELING_GUIDE.md) to learn how to create models that follow `S2DM`.
You should be able to create your first valid specification files compliant to the `GraphQL SDL` and `SKOS`.

Once you have the specificaiton files, you could proceed to use [the tools](src/tools/).


## Continuous Integration

This project uses GitHub Actions for continuous integration and testing. Tests are automatically run on all branches when code is pushed or pull requests are created.

### Workflow

The project uses a single CI workflow (`ci.yml`) that runs:

1. **Pre-commit Checks** (on Ubuntu):
   - Runs all pre-commit hooks
   - Uses Python 3.11

2. **Test Suite** (Matrix Build):
   - Operating Systems: Ubuntu, macOS, Windows
   - Python Versions: 3.11, 3.12
   - Includes:
     - Ruff linting and formatting
     - MyPy type checking
     - Pytest with coverage reporting

### Running Tests Locally

To run the tests locally, ensure you have `uv` installed and run:

```bash
# Install dependencies
uv pip install -e .
uv pip install --group dev

# Run pre-commit hooks
uv tool run pre-commit run --all-files

# Run tests with coverage
uv run pytest --cov=src/s2dm --cov-report=term-missing

# Run linting and type checking
uv run ruff check .
uv run ruff format --check .
uv run mypy .
```

## Contributing

See [here](docs/CONTRIBUTING.md) if you would like to contribute.
