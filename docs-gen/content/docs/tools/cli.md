---
title: Command Line Interface (CLI)
weight: 100
chapter: false
---

## Compose Command

The `compose` command merges multiple GraphQL schema files into a single unified schema file. It automatically adds `@reference` directives to track which file each type was obtained from.

### Basic Usage

```bash
s2dm compose -s <schema1> -s <schema2> -o <output_file>
```

### Options

- `-s, --schema PATH`: GraphQL schema file or directory (required, can be specified multiple times)
- `-r, --root-type TEXT`: Root type name for filtering the schema (optional)
- `-q, --selection-query PATH`: GraphQL query file for filtering schema based on selected fields (optional)
- `-n, --naming-config PATH`: YAML file with naming configuration for transforming type and field names (optional)
- `-e, --expanded-instances`: Transform instance tag arrays into nested structures (optional)
- `-o, --output FILE`: Output file path (required)

### Examples

#### Compose Multiple Schema Files

Merge multiple GraphQL schema files into a single output:

```bash
s2dm compose -s schema1.graphql -s schema2.graphql -o composed.graphql
```

#### Compose from Directories

Merge all `.graphql` files from multiple directories:

```bash
s2dm compose -s ./schemas/vehicle -s ./schemas/person -o composed.graphql
```

### Reference Directives

The compose command automatically adds `@reference(source: String!)` directives to all types to track their source:

```graphql
type Vehicle @reference(source: "schema1.graphql") {
  id: ID!
  name: String
}

type Person @reference(source: "schema2.graphql") {
  id: ID!
  name: String
}
```

Types from the S2DM specification (common types, scalars, directives) are marked with:

```graphql
type InCabinArea2x2 @instanceTag @reference(source: "S2DM Spec") {
  row: TwoRowsInCabinEnum
  column: TwoColumnsInCabinEnum
}
```

**Note:** If a type already has a `@reference` directive in the source schema, it will be preserved and not overwritten.

#### Filter by Root Type

See [Root Type Filtering](#root-type-filtering) for details.

```bash
s2dm compose -s schema.graphql --root-type Vehicle -o filtered.graphql
```

#### Filter by Selection Query

See [Selection Query Filtering](#selection-query-filtering) for details.

```bash
s2dm compose -s schema.graphql -q query.graphql -o filtered.graphql
```

#### With Naming Configuration

See [Naming Configuration](#naming-configuration) for details.

```bash
s2dm compose -s schema.graphql -n naming.yaml -o output.graphql
```

#### With Expanded Instances

See [Expanded Instances](#expanded-instances) for details.

```bash
s2dm compose -s schema.graphql --expanded-instances -o output.graphql
```

## Export Commands

### JSON Schema

This exporter translates the given GraphQL schema to [JSON Schema](https://json-schema.org/) format.

#### Key Features

- **Complete GraphQL Type Support**: Handles all GraphQL types including scalars, objects, enums, unions, interfaces, and lists
- **Selection Query**: Use the `--selection-query` flag to specify which types and fields to export via a GraphQL query. See [Selection Query Filtering](#selection-query-filtering) for more details.
- **Root Type Filtering**: Use the `--root-type` flag to export only a specific type and its dependencies
- **Naming Configuration**: Use the `--naming-config` flag to transform type and field names during export. See [Naming Configuration](#naming-configuration) for more details.
- **Expanded Instance Tags**: Use the `--expanded-instances` flag to transform instance tag arrays into nested object structures
- **Strict Nullability Mode**: Use the `--strict` flag to enforce GraphQL nullability in JSON Schema validation
- **Directive Support**: Converts S2DM directives like `@cardinality`, `@range`, and `@noDuplicates` to JSON Schema constraints
- **Reference-based Output**: Uses JSON Schema `$ref` for type references, creating clean and maintainable schemas

#### Example Transformation

Consider the following GraphQL schema:

```gql
directive @instanceTag on OBJECT
directive @metadata(comment: String, vssType: String) on FIELD_DEFINITION | OBJECT

type Vehicle @metadata(comment: "Vehicle entity", vssType: "branch") {
    id: ID!
    door: Door!
}

type Door {
    locked: Boolean!
    instanceTag: InCabinArea2x3
}

enum TwoRowsInCabinEnum {
    ROW1
    ROW2
}

enum ThreeColumnsInCabinEnum {
    DRIVERSIDE
    MIDDLE
    PASSENGERSIDE
}

type InCabinArea2x3 @instanceTag {
    row: TwoRowsInCabinEnum
    column: ThreeColumnsInCabinEnum
}
```

The JSON Schema exporter with `--expanded-instances` produces:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$defs": {
    "Vehicle": {
      "additionalProperties": false,
      "properties": {
        "id": {
          "type": "string"
        },
        "Door": {
          "$ref": "#/$defs/Door_Row"
        }
      },
      "type": "object",
      "$comment": "Vehicle entity",
      "x-metadata": {
        "vssType": "branch"
      },
      "required": [
        "id",
        "Door"
      ]
    },
    "Door": {
      "additionalProperties": false,
      "properties": {
        "locked": {
          "type": "boolean"
        }
      },
      "type": "object",
      "required": [
        "locked"
      ]
    },
    "Door_Row": {
      "additionalProperties": false,
      "properties": {
        "ROW1": {
          "$ref": "#/$defs/Door_Column"
        },
        "ROW2": {
          "$ref": "#/$defs/Door_Column"
        }
      },
      "type": "object"
    },
    "Door_Column": {
      "additionalProperties": false,
      "properties": {
        "DRIVERSIDE": {
          "$ref": "#/$defs/Door"
        },
        "MIDDLE": {
          "$ref": "#/$defs/Door"
        },
        "PASSENGERSIDE": {
          "$ref": "#/$defs/Door"
        }
      },
      "type": "object"
    }
  },
  "title": "Vehicle",
  "$ref": "#/$defs/Vehicle"
}
```

#### Root Type Filtering

Use the `--root-type` flag to export only a specific type and its dependencies:

```bash
s2dm export jsonschema --schema schema.graphql --output vehicle.json --root-type Vehicle
```

This creates a JSON Schema that references the Vehicle type as the root:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Vehicle",
  "$ref": "#/$defs/Vehicle",
  "$defs": {
    "Vehicle": { ... },
    "Engine": { ... },
    "FuelType": { ... }
  }
}
```

#### Directive Support

S2DM directives are converted to JSON Schema constraints:

- `@cardinality(min: 1, max: 5)` → `"minItems": 1, "maxItems": 5`
- `@range(min: 0.0, max: 100.0)` → `"minimum": 0.0, "maximum": 100.0`
- `@noDuplicates` → `"uniqueItems": true`
- `@metadata(comment: "Description", vssType: "branch")` → `"$comment": "Description", "x-metadata": {"vssType": "branch"}`
- Custom directives → `"x-directiveName": true` or `"x-directiveName": {...}`

#### Strict Nullability Mode

The `--strict` flag enforces GraphQL field nullability in the resulting JSON Schema:

```bash
s2dm export jsonschema --schema schema.graphql --output schema.json --strict
```

##### Examples

Given this GraphQL schema:

```graphql
type Vehicle {
  id: ID!                    # Non-null
  description: String        # Nullable
  year: Int                  # Nullable
  category: VehicleCategory  # Nullable enum
  parts: [Part]              # Nullable list of nullable parts
  doors: [Door!]!            # Non-null list of non-null doors
  wheels: [Wheel]!           # Non-null list of nullable wheels
}

enum VehicleCategory {
  CAR
  TRUCK
}
```

**Default mode** produces:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$defs": {
    "Vehicle": {
      "additionalProperties": false,
      "properties": {
        "id": {
          "type": "string"
        },
        "description": {
          "type": "string"
        },
        "category": {
          "$ref": "#/$defs/VehicleCategory"
        },
        "doorsOptional": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Door"
          }
        },
        "doorsRequired": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Door"
          }
        },
        "doors": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Door"
          }
        }
      },
      "type": "object",
      "required": [
        "id",
        "doorsRequired",
        "doors"
      ]
    },
    "Door": {
      "additionalProperties": false,
      "properties": {
        "id": {
          "type": "string"
        }
      },
      "type": "object",
      "required": [
        "id"
      ]
    },
    "VehicleCategory": {
      "type": "string",
      "enum": [
        "CAR",
        "TRUCK"
      ]
    }
  },
  "title": "Vehicle",
  "$ref": "#/$defs/Vehicle"
}
```

**Strict mode** produces:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$defs": {
    "Vehicle": {
      "additionalProperties": false,
      "properties": {
        "id": {
          "type": "string"
        },
        "description": {
          "type": [
            "string",
            "null"
          ]
        },
        "category": {
          "oneOf": [
            {
              "$ref": "#/$defs/VehicleCategory"
            },
            {
              "type": "null"
            }
          ]
        },
        "doorsOptional": {
          "oneOf": [
            {
              "type": "array",
              "items": {
                "oneOf": [
                  {
                    "$ref": "#/$defs/Door"
                  },
                  {
                    "type": "null"
                  }
                ]
              }
            },
            {
              "type": "null"
            }
          ]
        },
        "doorsRequired": {
          "type": "array",
          "items": {
            "oneOf": [
              {
                "$ref": "#/$defs/Door"
              },
              {
                "type": "null"
              }
            ]
          }
        },
        "doors": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Door"
          }
        }
      },
      "type": "object",
      "required": [
        "id",
        "doorsRequired",
        "doors"
      ]
    },
    "Door": {
      "additionalProperties": false,
      "properties": {
        "id": {
          "type": "string"
        }
      },
      "type": "object",
      "required": [
        "id"
      ]
    },
    "VehicleCategory": {
      "type": "string",
      "enum": [
        "CAR",
        "TRUCK"
      ]
    }
  },
  "title": "Vehicle",
  "$ref": "#/$defs/Vehicle"
}
```

##### Nullability Rules

| GraphQL Type | Strict Mode JSON Schema |
|-------------|------------------------|
| `String` | `{"type": ["string", "null"]}` |
| `String!` | `{"type": "string"}` |
| `VehicleType` (enum) | `{"oneOf": [{"$ref": "#/$defs/VehicleType"}, {"type": "null"}]}` |
| `VehicleType!` (enum) | `{"$ref": "#/$defs/VehicleType"}` |
| `[String]` | Array and items both nullable |
| `[String!]` | Array nullable, items non-null |
| `[String]!` | Array non-null, items nullable |
| `[String!]!` | Array and items both non-null |

You can call the help for usage reference:

```bash
s2dm export jsonschema --help
```

### Protocol Buffers (Protobuf)

This exporter translates the given GraphQL schema to [Protocol Buffers](https://protobuf.dev/) (`.proto`) format.

#### Key Features

- **Complete GraphQL Type Support**: Handles all GraphQL types including scalars, objects, enums, unions, interfaces, and lists
- **Selection Query (Required)**: Use the `--selection-query` flag to specify which types and fields to export via a GraphQL query
- **Root Type Filtering**: Use the `--root-type` flag to export only a specific type and its dependencies
- **Flatten Naming Mode**: Use the `--flatten-naming` flag to flatten nested structures into a single message with prefixed field names
- **Expanded Instance Tags**: Use the `--expanded-instances` flag to transform instance tag arrays into nested message structures
- **Field Nullability**: Properly handles nullable vs non-nullable fields from GraphQL schema
- **Directive Support**: Converts S2DM directives like `@cardinality`, `@range`, and `@noDuplicates` to protovalidate constraints
- **Package Name Support**: Use the `--package-name` flag to specify a protobuf package namespace

#### Example Transformation

Consider the following GraphQL schema and selection query:

GraphQL Schema:

```graphql
type Cabin {
  doors: [Door]
  temperature: Float
}

type Door {
  isLocked: Boolean
  instanceTag: DoorPosition
}

type DoorPosition @instanceTag {
  row: RowEnum
  side: SideEnum
}

enum RowEnum {
  ROW1
  ROW2
}

enum SideEnum {
  DRIVERSIDE
  PASSENGERSIDE
}

type Query {
  cabin: Cabin
}
```

Selection Query:

```graphql
query Selection {
  cabin {
    doors {
      isLocked
      instanceTag {
        row
        side
      }
    }
    temperature
  }
}
```

The Protobuf exporter produces:

> See [Selection Query](#selection-query-required) for more details on the command.

```protobuf
syntax = "proto3";

import "google/protobuf/descriptor.proto";
import "buf/validate/validate.proto";

extend google.protobuf.MessageOptions {
  string source = 50001;
}

message RowEnum {
  option (source) = "RowEnum";

  enum Enum {
    ROWENUM_UNSPECIFIED = 0;
    ROW1 = 1;
    ROW2 = 2;
  }
}

message SideEnum {
  option (source) = "SideEnum";

  enum Enum {
    SIDEENUM_UNSPECIFIED = 0;
    DRIVERSIDE = 1;
    PASSENGERSIDE = 2;
  }
}

message DoorPosition {
  option (source) = "DoorPosition";

  RowEnum.Enum row = 1;
  SideEnum.Enum side = 2;
}

message Cabin {
  option (source) = "Cabin";

  repeated Door doors = 1;
  float temperature = 2;
}

message Door {
  option (source) = "Door";

  bool isLocked = 1;
  DoorPosition instanceTag = 2;
}

message Selection {
  option (source) = "Query";

  optional Cabin cabin = 1;
}
```

> The `Query` type from the GraphQL schema is renamed to match the selection query operation name (`Selection` in this example).

#### Selection Query (Required)

The protobuf exporter requires a selection query to determine which types and fields to export:

```bash
s2dm export protobuf --schema schema.graphql --selection-query query.graphql --output cabin.proto
```

See the [Selection Query Filtering](#selection-query-filtering) section for details on how selection queries work.

#### Root Type Filtering

The `--root-type` flag can be used to further filter the export. See the [Root Type Filtering](#root-type-filtering) section for details.

#### Flatten Naming Mode

Use the `--flatten-naming` flag to flatten nested object structures into a single message with prefixed field names. This mode works with the selection query to flatten all root-level types selected in the query:

```bash
s2dm export protobuf --schema schema.graphql --selection-query query.graphql --output vehicle.proto --flatten-naming
```

You can optionally combine it with `--root-type` to flatten only a specific root type:

```bash
s2dm export protobuf --schema schema.graphql --selection-query query.graphql --output vehicle.proto --root-type Vehicle --flatten-naming
```

**Example transformation:**

Given a GraphQL schema and the selection query:

GraphQL Schema:

```graphql
type Vehicle {
  adas: ADAS
}

type ADAS {
  abs: ABS
}

type ABS {
  isEngaged: Boolean
}

type Query {
  vehicle: Vehicle
}
```

Selection Query:

```graphql
query Selection {
  vehicle {
    adas {
      abs {
        isEngaged
      }
    }
  }
}
```

Flatten mode produces:

```protobuf
syntax = "proto3";

import "google/protobuf/descriptor.proto";
import "buf/validate/validate.proto";

extend google.protobuf.MessageOptions {
  string source = 50001;
}

message Selection {
  bool Vehicle_adas_abs_isEngaged = 1;
}

```

> The output message name is derived from the selection query operation name (`Selection` in this example).

#### Expanded Instance Tags

The `--expanded-instances` flag transforms instance tag objects into nested message structures instead of repeated fields. This provides compile-time type safety for accessing specific instances.

```bash
s2dm export protobuf --schema schema.graphql --selection-query query.graphql --output cabin.proto --expanded-instances
```

**Default behavior (without flag):**

Given a GraphQL schema with instance tags and a selection query:

GraphQL Schema:

```graphql
type Cabin {
  doors: [Door]
}

type Door {
  isLocked: Boolean
  instanceTag: DoorPosition
}

type DoorPosition @instanceTag {
  row: RowEnum
  side: SideEnum
}

enum RowEnum {
  ROW1
  ROW2
}

enum SideEnum {
  DRIVERSIDE
  PASSENGERSIDE
}

type Query {
  cabin: Cabin
}
```

Selection Query:

```graphql
query Selection {
  cabin {
    doors {
      isLocked
      instanceTag {
        row
        side
      }
    }
  }
}
```

Default output uses repeated fields and includes the instanceTag field:

```protobuf
syntax = "proto3";

import "google/protobuf/descriptor.proto";
import "buf/validate/validate.proto";

extend google.protobuf.MessageOptions {
  string source = 50001;
}

message RowEnum {
  option (source) = "RowEnum";

  enum Enum {
    ROWENUM_UNSPECIFIED = 0;
    ROW1 = 1;
    ROW2 = 2;
  }
}

message SideEnum {
  option (source) = "SideEnum";

  enum Enum {
    SIDEENUM_UNSPECIFIED = 0;
    DRIVERSIDE = 1;
    PASSENGERSIDE = 2;
  }
}

message Door {
  option (source) = "Door";

  optional bool isLocked = 1;
  optional DoorPosition instanceTag = 2;
}


message Cabin {
  option (source) = "Cabin";

  repeated Door doors = 1;
}


message DoorPosition {
  option (source) = "DoorPosition";

  optional RowEnum.Enum row = 1;
  optional SideEnum.Enum side = 2;
}

message Selection {
  option (source) = "Query";

  optional Cabin cabin = 1;
}
```

**With `--expanded-instances` flag:**

The same schema and selection query produce nested messages representing the cartesian product of instance tag values:

```protobuf
syntax = "proto3";

import "google/protobuf/descriptor.proto";
import "buf/validate/validate.proto";

extend google.protobuf.MessageOptions {
  string source = 50001;
}

message RowEnum {
  option (source) = "RowEnum";

  enum Enum {
    ROWENUM_UNSPECIFIED = 0;
    ROW1 = 1;
    ROW2 = 2;
  }
}

message SideEnum {
  option (source) = "SideEnum";

  enum Enum {
    SIDEENUM_UNSPECIFIED = 0;
    DRIVERSIDE = 1;
    PASSENGERSIDE = 2;
  }
}

message Door {
  option (source) = "Door";

  optional bool isLocked = 1;
}

message Cabin {
  option (source) = "Cabin";

  Door_Row Door = 1 [(buf.validate.field).required = true];
}

message Door_Side {
  option (source) = "Door_Side";

  optional Door DRIVERSIDE = 1;
  optional Door PASSENGERSIDE = 2;
}

message Door_Row {
  option (source) = "Door_Row";

  Door_Side ROW1 = 1 [(buf.validate.field).required = true];
  Door_Side ROW2 = 2 [(buf.validate.field).required = true];
}

message Selection {
  option (source) = "Query";

  optional Cabin cabin = 1;
}
```

**Key differences:**

- Instance tag enums (`RowEnum`, `SideEnum`) remain in the output
- Types with `@instanceTag` directive (`DoorPosition`) are excluded from the output
- The `instanceTag` field is excluded from the Door message
- Intermediate types (`Door_Row`, `Door_Side`) are created as top-level messages
- Field names use the type name (`Door` not `doors`)
- The field becomes required and non-repeated

#### Directive Support

S2DM directives are converted to [protovalidate](https://github.com/bufbuild/protovalidate) constraints:

- `@range(min: 0, max: 100)` → `[(buf.validate.field).int32 = {gte: 0, lte: 100}]`
- `@noDuplicates` → `[(buf.validate.field).repeated = {unique: true}]`
- `@cardinality(min: 1, max: 5)` → `[(buf.validate.field).repeated = {min_items: 1, max_items: 5}]`

GraphQL Schema:

```graphql
type Vehicle {
  speed: Int @range(min: 0, max: 300)
  tags: [String] @noDuplicates @cardinality(min: 1, max: 10)
}

type Query {
  vehicle: Vehicle
}
```

Selection Query:

```graphql
query Selection {
  vehicle {
    speed
    tags
  }
}
```

Produces:

```protobuf
syntax = "proto3";

import "google/protobuf/descriptor.proto";
import "buf/validate/validate.proto";

extend google.protobuf.MessageOptions {
  string source = 50001;
}

message Vehicle {
  option (source) = "Vehicle";

  int32 speed = 1 [(buf.validate.field).int32 = {gte: 0, lte: 300}];
  repeated string tags = 2 [(buf.validate.field).repeated = {unique: true, min_items: 1, max_items: 10}];
}

message Selection {
  option (source) = "Query";

  optional Vehicle vehicle = 1;
}
```

#### Type Mappings

GraphQL types are mapped to protobuf types as follows:

| GraphQL Type | Protobuf Type |
|--------------|---------------|
| `String`     | `string`      |
| `Int`        | `int32`       |
| `Float`      | `float`       |
| `Boolean`    | `bool`        |
| `ID`         | `string`      |
| `Int8`       | `int32`       |
| `UInt8`      | `uint32`      |
| `Int16`      | `int32`       |
| `UInt16`     | `uint32`      |
| `UInt32`     | `uint32`      |
| `Int64`      | `int64`       |
| `UInt64`     | `uint64`      |

**List types** are converted to `repeated` fields:

- `[String]` → `repeated string`
- `[Int]` → `repeated int32`

**Enums** are converted to protobuf enums wrapped in a message:

- Each GraphQL enum becomes a protobuf message with the same name
- Inside the message, an `Enum` nested enum is created
- An `UNSPECIFIED` value is added at position 0
- References use the `.Enum` suffix (e.g., `LockStatus.Enum`)

**Field Nullability:**

GraphQL field nullability is preserved in protobuf using the `optional` keyword and protovalidate constraints:

- **Nullable fields** (e.g., `name: String`) → `optional` proto3 fields
- **Non-nullable fields** (e.g., `id: ID!`) → fields with `[(buf.validate.field).required = true]`

Example:

```graphql
type User {
  id: ID!              # Non-nullable
  name: String         # Nullable
}
```

Produces:

```protobuf
message User {
  option (source) = "User";

  string id = 1 [(buf.validate.field).required = true];
  optional string name = 2;
}
```

You can call the help for usage reference:

```bash
s2dm export protobuf --help
```

#### Field Number Stability

**Important Limitation**: Field numbers in generated protobuf files are **not stable** across schema regenerations when the GraphQL schema changes.

**How Field Numbers Are Assigned:**

Field numbers are assigned sequentially (starting from 1) based on:

1. The iteration order of fields in the GraphQL schema
2. Which types/fields are included (affected by `--root-type` filtering)
3. The flattening logic (when using `--flatten-naming`)

**Impact on Schema Evolution:**

Any change to the GraphQL schema can cause field number reassignments:

```graphql
# Version 1
type Door {
  isLocked: Boolean    # becomes field number 1
  position: Int        # becomes field number 2
}

# Version 2 - Adding a new field
type Door {
  id: ID               # becomes field number 1
  isLocked: Boolean    # becomes field number 2 (was 1!)
  position: Int        # becomes field number 3 (was 2!)
}
```

**When Field Number Stability Matters:**

Field number changes break compatibility if you have:

- **Persistent protobuf data**: Data stored in databases, files, or caches will deserialize incorrectly after regeneration
- **Rolling deployments**: Services using different schema versions cannot communicate during deployment
- **Message queues**: Messages enqueued before regeneration will fail to deserialize correctly
- **Archived data**: Historical protobuf-encoded logs or backups become unreadable

## Common Features

### Selection Query Filtering

All export commands (except for protobuf where it's required) and the compose command support the `--selection-query` flag to filter the schema based on a GraphQL query.

#### Usage

```bash
s2dm export <format> --selection-query query.graphql ...
```

Or with the compose command:

```bash
s2dm compose --selection-query query.graphql ...
```

#### Behavior

Given a query file `query.graphql`:

```graphql
query Selection {
  vehicle(instance: "id") {
    averageSpeed
    adas {
      abs {
        isEngaged
      }
    }
  }
}
```

The filtered schema will include:

- Only the selected types: `vehicle`, `adas`, `abs`
- Only the selected fields within each type
- Types referenced by field arguments (e.g., enums used in field arguments)
- Only directive definitions that are actually used in the filtered schema

**Note:** The query must be valid against the schema. Root fields in the query (e.g., `vehicle`) must exist in the `Query` type of the schema.

### Root Type Filtering

All export commands and the compose command support the `--root-type` flag to filter the schema to only a specific type and its transitive dependencies.

#### Usage

```bash
s2dm export <format> --root-type Vehicle ...
```

Or with the compose command:

```bash
s2dm compose --root-type Vehicle ...
```

#### Behavior

When you specify a root type:

```bash
s2dm compose -s schema.graphql -o composed.graphql -r Vehicle
```

The output will include:

- The `Vehicle` type
- All types transitively referenced by `Vehicle`
- Enums used in fields of these types
- Scalar types used in fields

> Types not connected to `Vehicle` will be filtered out.

**Combining with Selection Query:**

When used with `--selection-query`, root type filtering is applied after the selection query filtering, further narrowing the results to only types reachable from the specified root type.

### Naming Configuration

All export commands and the compose command support a naming configuration feature that allows you to transform element names using the `--naming-config` flag.

Apply naming configuration to any export command:

```bash
s2dm export <format> --naming-config naming.yaml ...
```

Or to the compose command:

```bash
s2dm compose --naming-config naming.yaml ...
```

#### Configuration Format

The naming configuration is defined in a YAML file with the following structure:

```yaml
# Transform type names by type context
type:
  object: PascalCase
  interface: PascalCase
  input: PascalCase
  enum: PascalCase
  union: PascalCase
  scalar: PascalCase

# Transform field names by type context
field:
  object: camelCase
  interface: camelCase
  input: snake_case

# Transform enum values (no context needed)
enumValue: MACROCASE

# Transform instanceTag field names (no context needed)
instanceTag: COBOL-CASE

# Transform argument names by context
argument:
  field: camelCase
```

#### Supported Case Formats

The naming configuration supports the following case conversion formats:

- **camelCase**: `myVariableName`
- **PascalCase**: `MyVariableName`
- **snake_case**: `my_variable_name`
- **kebab-case**: `my-variable-name`
- **MACROCASE**: `MY_VARIABLE_NAME`
- **COBOL-CASE**: `MY-VARIABLE-NAME`
- **flatcase**: `myvariablename`
- **TitleCase**: `My Variable Name`

#### Example Conversion

Given this GraphQL schema:

```graphql
type vehicle_info {
  avg_speed: Float
  fuel_type: fuel_type_enum
}

enum fuel_type_enum {
  GASOLINE_TYPE
  DIESEL_TYPE
}
```

And this naming configuration:

```yaml
type:
  object: PascalCase
  enum: PascalCase
field:
  object: camelCase
enumValue: PascalCase
```

The exported schema will transform names as follows:

- Type: `vehicle_info` → `VehicleInfo`
- Field: `avg_speed` → `avgSpeed`
- Field: `fuel_type` → `fuelType`
- Enum type: `fuel_type_enum` → `FuelTypeEnum`
- Enum values: `GASOLINE_TYPE` → `GasolineType`, `DIESEL_TYPE` → `DieselType`

#### Validation Rules

The naming configuration system enforces several validation rules to ensure consistency and correctness:

**Element Type Validation:**

- **Valid element types**: Only `type`, `field`, `argument`, `enumValue`, and `instanceTag` are allowed
- **Context restrictions**: Some element types cannot have context-specific configurations:
  - `enumValue` and `instanceTag` are contextless and use a single case format
  - `argument` can only have `field` context
- **Value type validation**: Element values must be either strings (case formats) or dictionaries (for context-specific configurations)

**Context Validation:**

- **Type contexts**: `object`, `interface`, `input`, `scalar`, `union`, `enum`
- **Field contexts**: `object`, `interface`, `input`
- **Argument contexts**: `field`

**Case Format Validation:**

- **Valid case formats**: `camelCase`, `PascalCase`, `snake_case`, `kebab-case`, `MACROCASE`, `COBOL-CASE`, `flatcase`, `TitleCase`
- **Format enforcement**: Only recognized case formats are accepted; invalid formats will cause validation errors

**Special Rules:**

- **EnumValue-InstanceTag pairing**: If `enumValue` is present in the configuration, `instanceTag` must also be present
- **InstanceTag preservation**: The literal field name `instanceTag` is never transformed, regardless of naming configuration, to preserve its semantic meaning

#### Notes

- Built-in GraphQL types (`String`, `Int`, `Float`, `Boolean`, `ID`, `Query`, `Mutation`, `Subscription`) are never transformed
- If a configuration is not provided for an element type, the original names are preserved
- Configuration is loaded once at the command level and applied consistently across the entire export or composition process

### Expanded Instances

All export commands and the compose command support the `--expanded-instances` flag that transforms instance tag arrays into nested structures.

#### Usage

```bash
s2dm export <format> --expanded-instances ...
```

Or with the compose command:

```bash
s2dm compose --expanded-instances ...
```

#### Transformation Behavior

Given a schema with instance tags:

```graphql
type Cabin {
  doors: [Door]
}

type Door {
  isLocked: Boolean
  instanceTag: DoorPosition
}

type DoorPosition @instanceTag {
  row: RowEnum
  side: SideEnum
}

enum RowEnum {
  ROW1
  ROW2
}

enum SideEnum {
  DRIVERSIDE
  PASSENGERSIDE
}
```

**Without `--expanded-instances` (default):**

The schema structure remains as-is with list fields and instanceTag preserved.

**With `--expanded-instances`:**

The schema is transformed to use nested intermediate types:

```graphql
type Cabin {
  Door: Door_Row
}

type Door_Row {
  ROW1: Door_Side
  ROW2: Door_Side
}

type Door_Side {
  DRIVERSIDE: Door
  PASSENGERSIDE: Door
}

type Door {
  isLocked: Boolean
}

enum RowEnum {
  ROW1
  ROW2
}

enum SideEnum {
  DRIVERSIDE
  PASSENGERSIDE
}
```

#### Key Changes

- **Field names**: Plural list fields (`doors`) are renamed to singular (`Door`)
- **Field types**: List types (`[Door]`) become intermediate types (`Door_Row`)
- **Intermediate types**: New types are created representing the cartesian product of instance tag enums (`Door_Row`, `Door_Side`)
- **Instance tag removal**: The `instanceTag` field is removed from the base type (`Door`)
- **Type removal**: Types with `@instanceTag` directive (`DoorPosition`) are removed from the schema
- **Enum preservation**: Instance tag enums (`RowEnum`, `SideEnum`) remain in the schema
