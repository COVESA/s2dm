# ID Generation Module

This module implements a deterministic ID generation mechanism for GraphQL schema elements. It generates unique identifiers based on the metadata that constitutes a breaking change when modified.

## Overview

The ID generation mechanism is designed to:
- Generate deterministic, unique IDs for schema elements
- Base IDs on elements that constitute breaking changes
- Support tracking of concept variations and realizations

## Components

### IDGenerationSpec

The `IDGenerationSpec` class is the core component that encapsulates all metadata required for ID generation. It was designed to:

1. **Capture Breaking Changes**: Only include fields that would constitute a breaking change when modified
2. **Support Concept Tracking**: Enable tracking of concept variations while maintaining semantic meaning
3. **Handle GraphQL Types**: Work seamlessly with GraphQL schema types and their metadata

#### Fields

| Field | Description | Example | Why It Matters |
|-------|-------------|---------|----------------|
| `name` | Fully qualified name of the field | `Window.position` | Identifies the concept |
| `data_type` | Data type of the field | `float`, `int`, `string` | Breaking change if type changes |
| `unit` | Unit of measurement | `PERCENT`, `DEGREE` | Breaking change if unit changes |
| `allowed` | Allowed enum values | `["OPEN", "CLOSED"]` | Breaking change if allowed values change |
| `minimum` | Minimum value | `0.0` | Breaking change if range changes |
| `maximum` | Maximum value | `100.0` | Breaking change if range changes |

### Field Resolution

The module resolves fields in the following order:

1. **Name Resolution**:
   - For branch nodes (objects): Uses the GraphQL type name directly
   - For leaf nodes (fields): Uses the field name with prefix

   ```graphql
   type Vehicle_ADAS_ABS {  # Resolves to Vehicle_ADAS_ABS
     isEnabled: Boolean  # Resolves to "Vehicle_ADAS_ABS.isEnabled"
   }
   ```

2. **Data Type Resolution**:
   - For scalar types: Uses lowercase type name (as per vss-tools implementation)
   - For enum types: Uses "string" (as per vss-tools implementation)
   ```graphql
   position: Float  # Resolves to "float"
   status: WindowStatusEnum  # Resolves to "string"
   ```

3. **Unit Resolution**:
   - Extracts from field arguments
   - Maps to actual unit values using unit lookup
   ```graphql
   position(unit: RelationUnitEnum = PERCENT): Float  # Resolves to "PERCENT"
   ```

4. **Range Resolution**:
   - Extracts from @range directive
   - Includes minimum and maximum values
   ```graphql
   position: Float @range(min: 0.0, max: 100.0)  # Resolves to min: 0.0, max: 100.0
   ```

## Design Decisions

### Dropping Node Type

The "node type" variable was dropped because:
- It added unnecessary complexity
- The type information is already available in the GraphQL type system
- It didn't contribute to identifying breaking changes

### Using GraphQL Type Name as FQN

We decided to use the GraphQL type name directly as the fully qualified name (FQN) because:
- It provides a clear, hierarchical structure
- It matches the schema's natural organization
- It simplifies the resolution process
- It maintains consistency with GraphQL's type system

For more details on this decision, see [Issue #32](https://atc-github.azure.cloud.bmw/q555872/s2dm/issues/32).

## Usage

```python
from idgen.spec import IDGenerationSpec
from idgen.idgen import fnv1_32_wrapper

# Create a spec from a GraphQL field
spec = IDGenerationSpec.from_field(
    prefix="Window",
    field_name="position",
    field=graphql_field,
    unit_lookup=unit_lookup
)

# Generate ID
id = fnv1_32_wrapper(spec, strict_mode=True)
```

## Example

#### Example

Given a .graphql file (test.graphql):

```graphql
type Query {
    vehicle: Vehicle
}

enum Velocity_Unit_Enum {
  KILOMETER_PER_HOUR
  METERS_PER_SECOND
}

enum Vehicle_ADAS_ActiveAutonomyLevel_Enum {
  SAE_0
  SAE_5
}


type Vehicle_ADAS {
  activeAutonomyLevel: Vehicle_ADAS_ActiveAutonomyLevel_Enum
  isAutoPowerOptimize: Boolean
  powerOptimizeLevel: Int @range(min: 0, max: 10)
}

type Vehicle {
  id: ID!
  averageSpeed(unit: Velocity_Unit_Enum = KILOMETER_PER_HOUR): Float
  adas: Vehicle_ADAS
}

```

and units.yaml as

```yaml
km/h:
  definition: Velocity measured in kilometers per hours
  unit: kilometer per hour
  quantity: velocity
  allowed-datatypes: ['numeric']
m/s:
  definition: Speed measured in meters per second
  unit: meters per second
  quantity: velocity
  allowed-datatypes: ['numeric']
```

Running this command:

```bash
uv run python src/tools/to_id.py -o output.json test.graphql units.yaml
```

would generate this output.json:

```json

{
   "Vehicle.averageSpeed": "0x9B020962",
   "Vehicle_ADAS.activeAutonomyLevel": "0xB6C7D51B",
   "Vehicle_ADAS.isAutoPowerOptimize": "0x1B10735A",
   "Vehicle_ADAS.powerOptimizeLevel": "0x1CAF066F"
}
```

If you want to see the "node identifier strings" (the strings that we generate the id hash from), you could change the logging level to DEBUG with:

```bash
LOG_LEVEL=debug uv run python src/tools/to_id.py -o output.json test.graphql units.yaml
```

## References

- [COVESA VSS Tools ID Documentation](https://github.com/COVESA/vss-tools/blob/master/docs/id.md)
- [Issue #32: ID Generation Design](https://atc-github.azure.cloud.bmw/q555872/s2dm/issues/32)
