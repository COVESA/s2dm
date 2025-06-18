# S2DM GraphQL to JSON Schema Converter

A command-line tool that converts GraphQL schemas to JSON Schema Draft 2020-12 format, with full property expansion and directive support. Designed for the S2DM specification.

## Features

- Converts to JSON Schema Draft 2020-12 with full property expansion
- Processes GraphQL directives for enhanced validation
- Integrates with S2DM Python toolchain
- Fast validation with helpful error messages

## Installation

```bash
git clone <repository>
cd jsonschema
npm install
npm run build
npm link  # Makes 's2dm-gql2jsonschema' command globally available
```

## Usage

```bash
# Convert GraphQL schema to JSON Schema
s2dm-gql2jsonschema schema.graphql

# Save to file
s2dm-gql2jsonschema schema.graphql -o output.json

# Show help
s2dm-gql2jsonschema --help
```

## Schema Requirements

Your GraphQL schema must have:
- A `Query` type with exactly one field
- That field represents your domain object
- Optional custom directives for validation

Example:
```graphql
directive @range(min: Int, max: Int) on FIELD_DEFINITION

type Query {
  vehicle: Vehicle  # Single domain field
}

type Vehicle {
  make: String
  year: Int @range(min: 1900, max: 2030)
}
```

## Supported Directives

- `@range(min: Int, max: Int)`: Adds numeric validation
- `@cardinality`: Specifies collection constraints
- See code for full list of supported directives

## Development

```bash
npm run build   # Build TypeScript
npm test        # Run tests
npm run lint    # Check code style
```

## Python Integration

```python
from s2dm.exporters.jsonschema import convert_graphql_to_jsonschema

# Use Python wrapper
convert_graphql_to_jsonschema("schema.graphql", "output.json")
```

## Contributing

See [CONTRIBUTING.md](../docs/CONTRIBUTING.md) for guidelines.
