# GraphQL to JSON Schema Converter

Convert GraphQL schemas to JSON Schema (Draft 2020-12) format with S2DM directive support.

## Usage

```bash
# Convert GraphQL schema to JSON Schema
s2dm export jsonschema -s examples/graphql-to-jsonschema/example.graphql -o examples/graphql-to-jsonschema/output.json
```

## Features

- Converts GraphQL schemas to JSON Schema Draft 2020-12
- Processes S2DM directives (e.g., @range, @cardinality)
- Expands all references for self-contained schemas
- Handles nested types and complex relationships

## Example

Input (`example.graphql`):
```graphql
type Query {
  vehicle: Vehicle
}

type Vehicle {
  id: ID!
  averageSpeed(unit: Velocity_Unit_Enum = KILOMETER_PER_HOUR): Int @range(min: 0.0, max: 999.9)
  isAutoPowerOptimize: Boolean
  occupant_s: [Vehicle_Occupant] @noDuplicates
}

type Vehicle_Occupant {
  id: ID!
  instanceLabel: String
}
```

Output (`output.json`):
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "properties": {
    "id": {
      "type": "string"
    },
    "averageSpeed": {
      "type": "number",
      "minimum": 0,
      "maximum": 999.9
    },
    "isAutoPowerOptimize": {
      "type": "boolean"
    },
    "occupant_s": {
      "type": "array",
      "items": {
        "anyOf": [
          {"$ref": "#/definitions/Vehicle_Occupant"},
          {"type": "null"}
        ]
      },
      "uniqueItems": true
    }
  },
  "type": "object",
  "title": "Vehicle",
  "additionalProperties": false,
  "required": ["id"]
}
```

## Supported Field Cases

The JSON Schema exporter supports all GraphQL field variations:

| Field Case | GraphQL Syntax | JSON Schema Output |
|------------|----------------|-------------------|
| **Nullable Singular** | `field: String` | `{"type": "string"}` |
| **Non-Nullable Singular** | `field: String!` | `{"type": "string"}` + required |
| **Nullable List** | `field: [String]` | Array with nullable items |
| **Non-Nullable List** | `field: [String]!` | Array + required |
| **Nullable List of Non-Null** | `field: [String!]` | Array with non-null items |
| **Non-Null List of Non-Null** | `field: [String!]!` | Array with non-null items + required |
| **Nullable Set** | `field: [String] @noDuplicates` | Array with `"uniqueItems": true` |
| **Non-Nullable Set** | `field: [String]! @noDuplicates` | Array with `"uniqueItems": true` + required |

### Set Fields Example

Input:
```graphql
type User {
  tags: [String] @noDuplicates
  categories: [String]! @noDuplicates
}
```

Output:
```json
{
  "properties": {
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "uniqueItems": true
    },
    "categories": {
      "type": "array",
      "items": {"type": "string"},
      "uniqueItems": true
    }
  },
  "required": ["categories"]
}
```

## Requirements

- Python 3.8+
- Node.js and npm (for the underlying converter)

The tool will automatically:
1. Find or build the converter CLI
2. Process the schema with S2DM extensions
3. Apply directive-based validations
4. Output clean, self-contained JSON Schema
