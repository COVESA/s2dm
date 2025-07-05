# S2DM Examples

This directory contains example files and commands to demonstrate how to use the S2DM tools with a sample GraphQL schema.

## Sample Files

- `sample.graphql` - A comprehensive GraphQL schema demonstrating vehicle data modeling
- Uses `units.yaml` for unit definitions

## Spec History Generation

Run init to initialize your first spec history file

```bash
s2dm registry init -s examples/spec-history-registry/sample.graphql -u examples/spec-history-registry/units.yaml -o spec_history/spec_history.json
```

This creates:

- `examples/spec_history.json` - JSON-LD file tracking realization history for each concept
- `examples/history/` directory - Individual GraphQL type definition files with timestamps

### Updating Spec History

Let's now use the updated "sample_updated.graphql" file to generate a new spec history.

The changes are:

```bash
▶ diff examples/spec-history-registry/sample.graphql examples/spec-history-registry/sample_updated.graphql
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
s2dm registry update -s examples/spec-history-registry/sample_updated.graphql -u examples/spec-history-registry/units.yaml -sh spec_history/spec_history.json -o spec_history/spec_history_updated.json
```

## Expected Output Files

After running all commands, you'll have:

```bash
examples
├── history
│   ├── Acceleration_Unit_Enum_20250618092822_0x48805230.graphql
│   ├── Angle_Unit_Enum_20250618092822_0x32CF16AC.graphql
│   ├── Angularspeed_Unit_Enum_20250618092822_0xBD584F20.graphql
│   ├── Datetime_Unit_Enum_20250618092822_0x3438A1BC.graphql
│   ├── Distancepervolume_Unit_Enum_20250618092822_0x06B888B9.graphql
│   ├── Duration_Unit_Enum_20250618092822_0xAAD783F9.graphql
│   ├── Electriccharge_Unit_Enum_20250618092822_0xBEF59642.graphql
...
├── spec_history.json
├── spec-history-registry
│   ├── README.md
│   ├── sample.graphql
│   ├── sample_updated.graphql
│   └── units.yaml
└── spec_history_updated.json
```

## Extra tools

These tools are embedded in the spec history generation but can also be called separately

### ID Generation

Generate unique identifiers for schema elements:

```bash
s2dm export id -s examples/spec-history-registry/sample.graphql -u examples/spec-history-registry/units.yaml -o examples/concept_ids.json
```

This creates `examples/concept_ids.json` with deterministic IDs for each field in the schema.

### Concept URI Generation

Generate semantic URIs for all concepts in the schema:

```bash
s2dm export concept-uri -s examples/spec-history-registry/sample.graphql -o examples/concept_uri.json --namespace "https://example.org/vss#" --prefix "ns"
```

This creates `examples/concept_uri.json` with JSON-LD formatted concept definitions.
