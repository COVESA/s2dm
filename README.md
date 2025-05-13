# Simplified Semantic Data Modeling (S2DM)
Welcome to the Simplified Semantic Data Modeling (S2DM) repository.
S2DM is an approach for modeling data of multiple domains.
It is **_simple_** in the sense that any Subject Matter Expert (SME) could contribute to a controlled vocabulary with minimal data modeling expertise.
Likewise, it is **_semantic_** in the sense that it specifies meaningful data structures, their cross-domain relationships, and arbitrary classification schemes.

> **Disclaimer:** Bear in mind the word `Simplified` in the name.
This approach aims to foster the adoption of (some) good data modeling practices.
It does not intent to re invent, nor to replace long-standing standards, such as those of the Semantic Web.
Hence, this approach does not incorporate advanced reasoning capabilities or the use of comprehensive ontologies typically associated with traditional semantic data modeling.


S2DM adopts data modeling best practices and reuses the following elements:
- [GraphQL Schema Definition Language (SDL)](https://graphql.org/learn/schema/).
It provides a clear, human-readable syntax for defining data structures and relationships, making it easy for SMEs to understand and use without requiring deep technical expertise.
- [SKOS](https://www.w3.org/2004/02/skos/).
It offers a straightforward framework for creating and managing hierarchical classifications and relationships between concepts, facilitating the organization and retrieval of knowledge in a way that is both intuitive and semantically rich..

To learn more about the background that has led to S2DM, as well as its design principles, please read the [S2DM Approach Primer](docs/s2dm_approach_primer.md).
## Repository Structure

- `docs/` - Documentation on usage, guidelines, and best practices.
- `spec/` - Contains specified models and SKOS files.
- `examples/` - Example application of S2DM to specific use cases.
- `src/` - Scripts that work on the specification files (e.g., exporting schemas, creating IRIs, etc.).

## Usage
### Getting Started
To get started with this repository, ...
> TODO: Add intial basic instructions.

### Exporting Specification
Use the provided scripts in the tools/ directory to export GraphQL schemas to different formats:
```bash
# TODO Add commands here...
```

### ID Generation

`to_id.py` script can be used for ID generation of a given graphql schema.
It generates a json output that has the fqn of a node and the ID of it as the key.

```bash
uv run python src/tools/to_id.py <path_to_schema.graphql> <path_to_units.yaml> -o output.json
```

For further information check out the [idgen readme](src/idgen/README.md).

### Concept URI Generation

The `to_concept_uri.py` script generates JSON-LD document representing the conceptual structure of a GraphQL schema. It creates URIs for all objects, fields, and enums in the schema, expressing their relationships in a semantic way.

```bash
python -m src.tools.to_concept_uri <path_to_schema.graphql> -o concept_uri.json --namespace "https://example.org/vss#" --prefix "ns"
```

### Spec History Generation

The `to_spec_history.py` script tracks changes in schema realizations over time. It maintains a history of realization IDs for each concept, enabling traceability of schema evolution.

```bash
# Initialize a new spec history
python -m src.tools.to_spec_history --concept-uri concept_uri.json --ids concept_ids.json --output spec_history.json --init

# Update an existing spec history
python -m src.tools.to_spec_history --concept-uri new_concept_uri.json --ids new_concept_ids.json --spec-history spec_history.json --output updated_spec_history.json --update
```

For more details on concept URI and spec history generation, refer to the [Tools README](src/tools/README.md).

### Further information
For detailed instructions on how to use the repository, refer to the [Usage Guide](docs/usage_guide.md).

## Contributing

See [here](docs/CONTRIBUTING.md) if you would like to contribute.

# License
> TODO: Add the corresponding license.

# Docs

at: https://pages.atc-github.azure.cloud.bmw/q555872/s2dm/approach/index.html
