# S2DM Examples

This directory contains example files and commands to demonstrate how to use the S2DM tools with a sample GraphQL schema.

## Sample Files

- `sample.graphql` - A comprehensive GraphQL schema demonstrating vehicle data modeling
- Uses `units.yaml` for unit definitions

## Running the Tools

Follow these commands in order to generate all the necessary files for the example:

### 1. ID Generation

Generate unique identifiers for schema elements:

```bash
# From the repository root
uv run python src/tools/to_id.py examples/sample.graphql examples/units.yaml -o examples/concept_ids.json
```

This creates `examples/concept_ids.json` with deterministic IDs for each field in the schema.

### 2. Concept URI Generation

Generate semantic URIs for all concepts in the schema:

```bash
# From the repository root
uv run python src/tools/to_concept_uri.py examples/sample.graphql -o examples/concept_uri.json --namespace "https://example.org/vss#" --prefix "ns"
```

This creates `examples/concept_uri.json` with JSON-LD formatted concept definitions.

### 3. Spec History Generation

Initialize a specification history registry to track schema evolution:

```bash
# Initialize spec history (first time)
uv run python src/tools/to_spec_history.py --concept-uri examples/concept_uri.json --ids examples/concept_ids.json --schema examples/sample.graphql --output examples/spec_history.json --history-dir examples/history --init
```

This creates:
- `examples/spec_history.json` - JSON-LD file tracking realization history for each concept
- `examples/history/` directory - Individual GraphQL type definition files with timestamps

### Updating Spec History

Let's now use the updated "sample_updated.graphql" file to generate a new spec history.

The changes are:

```bash
▶ diff examples/sample.graphql examples/sample_updated.graphql
13a14
>   COLLISION_PREVENTION
28c29
<   averageSpeed(unit: Velocity_Unit_Enum = KILOMETER_PER_HOUR): Float
---
>   averageSpeed(unit: Velocity_Unit_Enum = KILOMETER_PER_HOUR): Int
54c55
<   distance(unit: Length_Unit_Enum = METER): Float
---
>   distance(unit: Length_Unit_Enum = METER): Int
```

1. Added a new enum value `COLLISION_PREVENTION` to the `Vehicle_ADAS_ObstacleDetection_WarningType_Enum`. This will now change the allowed values of `Vehicle_ADAS_ObstacleDetection.warningType`

2. Changed `Vehicle.averageSpeed` from `Float` -> `Int`

3. Changed `Vehicle_ADAS_ObstacleDetection.distance` from `Float` -> `Int`


```bash
# Let's regenerate IDs and concept URIs:

uv run python src/tools/to_id.py examples/sample_updated.graphql examples/units.yaml -o examples/concept_ids_updated.json

uv run python src/tools/to_concept_uri.py examples/sample_updated.graphql -o examples/concept_uri_updated.json --namespace "https://example.org/vss#" --prefix "ns"

uv run python src/tools/to_spec_history.py --concept-uri examples/concept_uri_updated.json --ids examples/concept_ids_updated.json --schema examples/sample_updated.graphql --spec-history examples/spec_history.json --output examples/spec_history_updated.json --history-dir examples/history --update
```

## Expected Output Files

After running all commands, you'll have:
```
examples/
├── README.md
├── sample.graphql
├── concept_ids.json # Field IDs
├── concept_ids_updated.json # Field IDs updated
├── concept_uri.json # Concept definitions
├── concept_uri_updated.json # Concept definitions updated
├── spec_history.json # Evolution history
├── spec_history_updated.json # Evolution history updated
└── history/ # Type definition snapshots
    ├── Vehicle_YYYYMMDDHHMMSS_0xXXXXXXXX.graphql
    ├── Vehicle_ADAS_YYYYMMDDHHMMSS_0xXXXXXXXX.graphql
    └── ... (other types)
```
