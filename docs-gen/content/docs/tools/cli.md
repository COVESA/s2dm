---
title: Command Line Interface (CLI)
weight: 1
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

#### Filter by Root Type

Compose only types reachable from a specific root type:

```bash
s2dm compose -s schema1.graphql -s schema2.graphql -o composed.graphql -r Vehicle
```

This will include only the `Vehicle` type and all types transitively referenced by it, filtering out unreferenced types like `Person` if they're not connected to `Vehicle`.

#### Filter by Selection Query

Compose only types and fields selected in a GraphQL query:

```bash
s2dm compose -s schema1.graphql -s schema2.graphql -q query.graphql -o composed.graphql
```

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

The composed schema will include:

- Only the selected types: `vehicle`, `adas`, `abs`
- Only the selected fields within each type
- Types referenced by field arguments (e.g., enums used in field arguments)
- Only directive definitions that are actually used in the filtered schema

**Note:** The query must be valid against the composed schema. Root fields in the query (e.g., `vehicle`) must exist in the `Query` type of the schema.

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

## Export Commands

### Protocol Buffers (Protobuf)

This exporter translates the given GraphQL schema to [Protocol Buffers](https://protobuf.dev/) (`.proto`) format.

#### Key Features

- **Complete GraphQL Type Support**: Handles all GraphQL types including scalars, objects, enums, unions, interfaces, and lists
- **Root Type Filtering**: Use the `--root-type` flag to export only a specific type and its dependencies
- **Flatten Naming Mode**: Use the `--flatten-naming` flag to flatten nested structures into a single message with prefixed field names
- **Expanded Instance Tags**: Use the `--expanded-instances` flag to transform instance tag arrays into nested message structures
- **Directive Support**: Converts S2DM directives like `@cardinality`, `@range`, and `@noDuplicates` to protovalidate constraints
- **Package Name Support**: Use the `--package-name` flag to specify a protobuf package namespace

#### Example Transformation

Consider the following GraphQL schema:

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
```

The Protobuf exporter produces:

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
```

#### Root Type Filtering

Use the `--root-type` flag to export only a specific type and its dependencies:

```bash
s2dm export protobuf --schema schema.graphql --output vehicle.proto --root-type Vehicle
```

This will include only the `Vehicle` type and all types transitively referenced by it.

#### Flatten Naming Mode

Use the `--flatten-naming` flag to flatten nested object structures into a single message with prefixed field names. This mode requires `--root-type` to be set:

```bash
s2dm export protobuf --schema schema.graphql --output vehicle.proto --root-type Vehicle --flatten-naming
```

**Example transformation:**

Given a GraphQL schema:

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
```

Flatten mode produces:

```protobuf
syntax = "proto3";

import "google/protobuf/descriptor.proto";
import "buf/validate/validate.proto";

extend google.protobuf.MessageOptions {
  string source = 50001;
}

message Message {
  bool Vehicle_adas_abs_isEngaged = 1;
}

```

#### Expanded Instance Tags

The `--expanded-instances` flag transforms instance tag objects into nested message structures instead of repeated fields. This provides compile-time type safety for accessing specific instances.

```bash
s2dm export protobuf --schema schema.graphql --output cabin.proto --expanded-instances
```

**Default behavior (without flag):**

Given a GraphQL schema with instance tags:

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

  bool isLocked = 1;
  DoorPosition instanceTag = 2;
}


message Cabin {
  option (source) = "Cabin";

  repeated Door doors = 1;
}


message DoorPosition {
  option (source) = "DoorPosition";

  RowEnum.Enum row = 1;
  SideEnum.Enum side = 2;
}
```

**With `--expanded-instances` flag:**

The same schema produces nested messages representing the cartesian product of instance tag values:

```protobuf
syntax = "proto3";

import "google/protobuf/descriptor.proto";
import "buf/validate/validate.proto";

extend google.protobuf.MessageOptions {
  string source = 50001;
}

message Door {
  option (source) = "Door";

  bool isLocked = 1;
}


message Cabin {
  option (source) = "Cabin";

  message Cabin_Door {
    message Cabin_Door_ROW1 {
      Door DRIVERSIDE = 1;
      Door PASSENGERSIDE = 2;
    }

    message Cabin_Door_ROW2 {
      Door DRIVERSIDE = 1;
      Door PASSENGERSIDE = 2;
    }

    Cabin_Door_ROW1 ROW1 = 1;
    Cabin_Door_ROW2 ROW2 = 2;
  }

  Cabin_Door Door = 1;
}
```

**Key differences:**

- Instance tag enums (`RowEnum`, `SideEnum`) are excluded from the output when using expanded instances
- Types with `@instanceTag` directive (`DoorPosition`) are excluded from the output
- The `instanceTag` field is excluded from the Door message
- Nested messages are created inside the parent message
- Field names use the GraphQL type name (`Door` not `doors`)

#### Directive Support

S2DM directives are converted to [protovalidate](https://github.com/bufbuild/protovalidate) constraints:

- `@range(min: 0, max: 100)` → `[(buf.validate.field).int32 = {gte: 0, lte: 100}]`
- `@noDuplicates` → `[(buf.validate.field).repeated = {unique: true}]`
- `@cardinality(min: 1, max: 5)` → `[(buf.validate.field).repeated = {min_items: 1, max_items: 5}]`

Example:

```graphql
type Vehicle {
  speed: Int @range(min: 0, max: 300)
  tags: [String] @noDuplicates @cardinality(min: 1, max: 10)
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

You can call the help for usage reference:

```bash
s2dm export protobuf --help
```

### Naming Configuration

All export commands support a global naming configuration feature that allows you to transform element names during the export process using the `[--naming-config | -n]` flag.

Apply naming configuration to any export command:

```bash
s2dm export [--naming-config | -n] naming.yaml ...
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
- Configuration is loaded once at the command level and applied consistently across the entire export process
