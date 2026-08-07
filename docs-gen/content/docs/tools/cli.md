---
title: Command Line Interface (CLI)
weight: 100
chapter: false
---

## Dependency Commands

### Resolve

The `deps resolve` command resolves dependencies from a dependency manifest, vendors the resolved schema and metadata into the workspace, and writes a lock file with integrity information.

#### Usage

```bash
s2dm deps resolve [--config CONFIG_PATH] [--identity IDENTITY_PATH] [--clean]
```

#### Options

- `--config CONFIG_PATH`: Path to the dependency manifest YAML file (optional, defaults to `s2dm.deps.yaml` in the current working directory)
- `--identity IDENTITY_PATH`: Path to the dependency identity YAML file containing remote access tokens (optional, defaults to `.s2dm.identity.yaml` in the current working directory when present)
- `--clean`: Resolve from a clean dependency state while restoring the previous lock file and vendored dependencies if resolution fails

#### Behavior

- Reads dependency entries from the dependency manifest.
- Resolves local dependencies from absolute source directories.
- Resolves remote dependencies from repository release assets.
- Uses configured identity tokens for authenticated remote release access when an identity file is provided.
- Validates that `metadata.yaml` matches the dependency name and version.
- Vendors resolved files to `.s2dm/vendor/<name>/<version>/`.
- Writes `s2dm.deps.lock` in the current working directory.
- Skips resolving a dependency when the vendored files already exist and match the dependency manifest, metadata, lock entry, and schema integrity.
- Creates a missing lock entry from an existing valid vendored dependency without re-downloading.
- Fails when a referenced vendored dependency does not match the dependency manifest, metadata, lock entry, or schema integrity.
- Removes vendored dependency targets that are no longer referenced by the dependency manifest.
- With `--clean`, moves the existing lock file and vendored dependencies aside temporarily, deletes those backups after success, and restores them if resolution fails.

#### Dependency Manifest

The default manifest file is `s2dm.deps.yaml`:

```yaml
dependencies:
  - name: Dependency
    version: "1.0.0"
    source: "/absolute/path/to/dependency"
    artifact: "schema.graphql"
    selection: "/path/to/selection/file"
```

Each dependency entry contains:

- `name`: Dependency name, which must match `metadata.yaml`
- `version`: Dependency version, which must match `metadata.yaml`
- `source`: Absolute local source directory or repository URL
- `artifact`: Dependency artifact name, such as `schema.graphql`, `bundle.zip`, `bundle.tar`, `bundle.tar.gz`, or `bundle.tgz`
- `selection` (optional): Path to a `.graphql` or `.gql` selection query file used to filter the dependency schema during `deps build`. Relative paths are resolved against the manifest directory, and the file must exist.

For direct GraphQL dependencies, the artifact must be named `schema.graphql` and `metadata.yaml` must exist next to it. For archive dependencies, the archive must contain `metadata.yaml` at its root and exactly one file named `schema.graphql` anywhere in the archive.

Remote dependencies are downloaded from release assets using this URL pattern:

```text
<repository-url>/releases/download/<version>/<artifact>
```

For example, `source: "https://github.com/owner/repo"`, `version: "1.0.0"`, and `artifact: "schema.graphql"` resolves the schema from:

```text
https://github.com/owner/repo/releases/download/1.0.0/schema.graphql
```

#### Identity File

For authenticated remote dependencies, `deps resolve` can read tokens from a dependency identity file.
If `--identity` is not provided, the command looks for `.s2dm.identity.yaml` in the current working directory.

> This file should not be committed.

The file format is:

```yaml
identities:
  - host: github.com
    token: <host-wide-token>
  - host: github.com
    scope: owner/repo
    token: <repository-token>
```

Each identity entry contains:

- `host`: Host name only, with optional port. Do not include a scheme, path, or credentials.
- `scope`: Optional repository scope in `owner/repo` form.
- `token`: Token used for authenticated release access.

Scoped entries take precedence over host-wide entries for the same host.
Duplicate host/scope entries are not allowed.

#### Output Files

- `.s2dm/vendor/<name>/<version>/schema.graphql`: Vendored dependency schema
- `.s2dm/vendor/<name>/<version>/metadata.yaml`: Vendored dependency metadata
- `s2dm.deps.lock`: Lock file containing resolved paths and schema integrity hashes

#### Examples

##### Resolve Default Manifest

Resolve dependencies from `s2dm.deps.yaml` in the current working directory:

```bash
s2dm deps resolve
```

##### Resolve Explicit Manifest

Resolve dependencies from a specific manifest path:

```bash
s2dm deps resolve --config path/to/deps/file
```

##### Clean Resolve

Resolve from a clean dependency state while preserving the previous lock file and vendored dependencies if resolution fails:

```bash
s2dm deps resolve --clean
```

##### Resolve with an Identity File

Resolve remote dependencies using an explicit identity file:

```bash
s2dm deps resolve --identity path/to/identity/file
```

##### Remote Dependency

Configure a dependency that is published as GitHub release assets:

```yaml
dependencies:
  - name: Dependency
    version: "1.0.0"
    source: "https://github.com/owner/repo"
    artifact: "schema.graphql"
```

### Build

The `deps build` command composes vendored dependency schemas into a single GraphQL SDL output file.

#### Usage

```bash
s2dm deps build [--config CONFIG_PATH] [--auto-prefix] --output <output_file>
```

#### Options

- `--config CONFIG_PATH`: Path to the dependency manifest YAML file (optional, defaults to `s2dm.deps.yaml` in the current working directory)
- `--auto-prefix`: Prefix conflicting dependency types using `preferred_prefix`, falling back to the dependency metadata `id`
- `-o, --output OUTPUT`: Output file path for the composed schema (required)

#### Behavior

- Reads dependency entries from the dependency manifest.
- Loads vendored dependency schemas from `.s2dm/vendor/<name>/<version>/schema.graphql`.
- Applies the dependency `selection` query when one is configured in the manifest.
- Detects duplicate type definitions across vendored dependencies.
- Fails when duplicate type names are found and `--auto-prefix` is not used.
- With `--auto-prefix`, rewrites conflicting type definitions and references before composing the final schema.
- Writes a single composed schema to the requested output path.

#### Prerequisites

- Vendored dependency schemas must already exist under `.s2dm/vendor/`.
- In the normal workflow, run `s2dm deps resolve` before `s2dm deps build`.

#### Examples

##### Build Vendored Dependencies

Compose all vendored dependency schemas into a single output file:

```bash
s2dm deps build --output composed.graphql
```

##### Build with Automatic Prefixing

Compose vendored schemas and automatically rename conflicting types:

```bash
s2dm deps build --output composed.graphql --auto-prefix
```

##### Build with a Custom Manifest

Use an explicit dependency manifest path:

```bash
s2dm deps build --config path/to/s2dm.deps.yaml --output composed.graphql
```

## Check Commands

### Constraints

The `check constraints` command validates your GraphQL schema to ensure correct usage of custom directives and naming conventions. This helps maintain consistency and catch errors early in the development process.

#### Usage

```bash
s2dm check constraints -s <schema_path>
```

#### Options

- `-s, --schema PATH`: GraphQL schema file or directory containing schema files (required, can be specified multiple times)
- `--naming-config PATH`: YAML file containing naming configuration to validate against (optional)

#### Validation Checks

The command performs the following validations:

1. **@instanceTag Rules**: Validates correct usage of the `@instanceTag` directive:
   - A field marked with `@instanceTag` must reference an object type that is itself marked with `@instanceTag`
   - An object may have at most one `@instanceTag` field
   - Every field of an `@instanceTag` object must be an enum
2. **@range Directive**: Ensures `min` value is less than or equal to `max` value
3. **@cardinality Directive**: Ensures `min` value is less than or equal to `max` value
4. **Naming Conventions** (optional): When `--naming-config` is provided, validates that type names, field names, enum values, and other elements follow the specified naming conventions

#### Examples

##### Basic Validation

Check a single schema file for directive constraint violations:

```bash
s2dm check constraints -s schema.graphql
```

##### Validate with Naming Configuration

Ensure your schema follows naming conventions defined in a YAML config file:

```bash
s2dm check constraints -s schema.graphql --naming-config naming.yaml
```

See [Naming Configuration](#naming-configuration) for details on the naming configuration format.

## Compose Command

The `compose` command merges multiple GraphQL schema files into a single unified schema file. If `@reference` is defined in the schema, it automatically adds `@reference` directives to track which file each type was obtained from.

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
- `--merge-shared-definitions`: Automatically reconcile compatible shared directive and scalar definitions across schemas (optional)
- `--ledger PATH`: Ledger directory used to annotate the schema with `@modl` directives (optional)
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

If `@reference(source: String!)` is defined in the schema, the compose command automatically adds `@reference(source: String!)` directives to all types to track their source:

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

### Shared Definitions

Composing multiple schemas reconciles their shared directives, scalars, and enums into a single set, declared once. Identical declarations merge; conflicting ones stop the build with a message naming the definition and its source schemas. Add `--merge-shared-definitions` to also reconcile compatible differences — one schema adding an optional directive argument or location, or an enum declaring extra values or directives — by keeping the most complete declaration.

```bash
s2dm compose -s schema1.graphql -s schema2.graphql --merge-shared-definitions -o composed.graphql
```

For example, two schemas declare the same directive — one with an extra optional argument and location:

```graphql
# schema1.graphql
directive @metadata(comment: String) on FIELD_DEFINITION

# schema2.graphql
directive @metadata(comment: String, source: String) on FIELD_DEFINITION | OBJECT
```

With `--merge-shared-definitions`, the composed output keeps the most complete declaration:

```graphql
directive @metadata(comment: String, source: String) on FIELD_DEFINITION | OBJECT
```

#### Enums

Enums are reconciled by name, following the same rule. Two declarations of the same enum are considered **identical** when they list the same value names and apply the same directives — both to the enum and to each value. Value order and descriptions are ignored, so those never cause a difference. Identical declarations collapse to one even without `--merge-shared-definitions`; the flag only affects declarations that differ.

When declarations of the same enum differ, the build stops with a conflict naming the enum and its source schemas (e.g. ``Multiple definitions of enum `Drivetrain` found in [schema1.graphql, schema2.graphql]``) — unless `--merge-shared-definitions` is set. With the flag, the composer keeps whichever declaration is a **superset** of every other:

- it declares every value the others declare, and may add more; and
- its directives — on the enum and on each shared value — include all of theirs, with matching argument values.

**Extra values.** Given `enum Drivetrain { FWD RWD }` and `enum Drivetrain { FWD RWD AWD }`, the flag keeps the declaration listing every value:

```graphql
enum Drivetrain {
  FWD
  RWD
  AWD
}
```

**Extra directives.** A directive added to the enum or to one of its values is a superset in the same way. Given `enum Drivetrain { FWD RWD }` and `enum Drivetrain { FWD RWD @deprecated(reason: "legacy") }`, the flag keeps the annotated declaration:

```graphql
enum Drivetrain {
  FWD
  RWD @deprecated(reason: "legacy")
}
```

**Irreconcilable declarations.** The flag only *selects* the most complete declaration among the inputs; it never synthesizes a new one by combining features. So when each declaration has something the other lacks — a value the other omits (`{ FWD RWD }` vs `{ FWD AWD }`), a directive the other omits, or the same directive with a different argument value (`@meta(note: "a")` vs `@meta(note: "b")`) — no declaration is a superset of the rest, and the build reports a conflict even with `--merge-shared-definitions`. Resolve it by editing one schema so its declaration is a true superset of the other.

### Ledger Annotation

Annotate the composed schema with `@modl` directives that link each object type, field, enum type, and enum value to its concept and contract in a [modl](https://github.com/COVESA/modl) ledger, matched by name.

```bash
s2dm compose -s schema.graphql --ledger ./ledger -o composed.graphql
```

Given a schema:

```graphql
type Car {
  id: ID!
}
```

and a ledger recording those elements:

```csv
# concepts.csv
serial,concept_uri,current_label,previous_labels,kind,status,parent_uri,instances
0,http://example/concepts/0,Car,,ENTITY,ACTIVE,,
1,http://example/concepts/1,Car.id,,PROPERTY,ACTIVE,http://example/concepts/0,
```

```csv
# contracts.csv
serial,concept_uri,contract_uri,revision_uri,status
0,http://example/concepts/0,http://example/contracts/0,http://example/revisions/0,ACTIVE
1,http://example/concepts/1,http://example/contracts/1,http://example/revisions/1,ACTIVE
```

compose produces:

```graphql
type Car @modl(concept: "http://example/concepts/0", contract: "http://example/contracts/0") {
  id: ID! @modl(concept: "http://example/concepts/1", contract: "http://example/contracts/1")
}
```

**Note:** The ledger directory must contain the modl `concepts.csv`, `contracts.csv`, `revisions.csv`, and `bindings.csv` files. If the schema and ledger do not describe the same set of elements, the schema is composed without `@modl` annotations.

## Export Commands

### JSON Tree

The `export json` command translates a GraphQL schema into a **hierarchical JSON tree** — a nested structure of branches and leaf signals. It is the primary S2DM output format and serves as the canonical human-readable representation of your domain model.

#### Key Features

- **Branch / leaf hierarchy**: Object types become branch nodes with a `children` map; scalar and enum fields become leaf nodes
- **Schema-intrinsic fields by default**: Only information encoded in the GraphQL schema itself is written — `description`, `datatype`, `min`, `max`, `unit`, `deprecated`
- **Raw datatype names**: Scalar and enum names are used as-is (e.g. `Float`, `Boolean`, `UInt8`, `GearPosition`)
- **Instance dimensions from `@instanceTag`**: When a field references an `@instanceTag` type, it is excluded as a child and its enum dimensions are written as an `instances` array on the parent branch instead
- **VSS metadata overlay** (`--vspec-meta`): Activates an optional YAML-based overlay that adds `type`, `comment`, `allowed`, `instances`, and other VSS-compatible keys — keyed by fully-qualified signal name (FQN)
- **VSS struct type handling** (`--vspec-meta`): Fields referencing `@vspec(element: STRUCT)` types are emitted as leaf nodes whose `datatype` is the struct's FQN, not expanded branches. Struct type definitions are rendered in a separate top-level `ComplexDataTypes` section built from the YAML
- **Root Type Filtering**: Use `--root-type` to export only one branch and its descendants
- **Selection Query**: Use `--selection-query` to narrow the export to a specific set of fields
- **Naming Configuration**: Use `--naming-config` to rename types and fields during export

#### Usage

```bash
s2dm export json -s <schema_path> -o <output_file>
```

#### Options

- `-s, --schema PATH`: GraphQL schema file or directory (required, can be specified multiple times)
- `-o, --output FILE`: Output JSON file path (required)
- `-r, --root-type TEXT`: Export only this type and its descendants (optional)
- `-q, --selection-query PATH`: GraphQL query file to filter exported fields (optional)
- `-n, --naming-config PATH`: YAML naming configuration for transforming names during export (optional)
- `-e, --expanded-instances`: Unfold `@instanceTag` arrays into nested types before exporting (optional)
- `--vspec-meta PATH`: YAML file with FQN-indexed VSS metadata overlay (optional — activates vspec-meta mode)

#### Default Mode

By default, only schema-intrinsic information is included. No `@vspec` annotations are processed and no `"type"` key is added to branch nodes.

Given this schema:

```graphql
directive @range(min: Float, max: Float) on FIELD_DEFINITION
directive @instanceTag on OBJECT

enum SideEnum { LEFT  RIGHT }

type MirrorTag @instanceTag {
  side: SideEnum
}

type Mirror {
  """Mirror pan as a percent."""
  pan: Float @range(min: -100, max: 100)
}

type Body {
  """All mirrors."""
  mirrors: Mirror
  instanceTag: MirrorTag
}

type Vehicle {
  body: Body
}
```

Running:

```bash
s2dm export json -s schema.graphql -o output.json -r Vehicle
```

Produces:

```json
{
  "Vehicle": {
    "children": {
      "body": {
        "children": {
          "mirrors": {
            "children": {
              "pan": {
                "description": "Mirror pan as a percent.",
                "datatype": "Float",
                "min": -100,
                "max": 100
              }
            },
            "description": "All mirrors.",
            "instances": [
              ["LEFT", "RIGHT"]
            ]
          }
        }
      }
    }
  }
}
```

Key behaviours to note:

- `instanceTag` does **not** appear as a child of `mirrors`
- Instead, the enum values of `SideEnum` are extracted and written as `"instances"` on `mirrors`
- Multi-dimensional tags produce one list per enum field (e.g. a `row` + `side` tag produces `[["ROW1","ROW2"], ["LEFT","RIGHT"]]`)

#### VSS Metadata Overlay (`--vspec-meta`)

Passing `--vspec-meta` activates vspec-meta mode. A flat YAML file keyed by dot-separated FQN is merged on top of each matching node. This enables producing VSS-compatible output without encoding VSS-specific information directly in the GraphQL schema.

```bash
s2dm export json -s schema.graphql -o output.json -r Vehicle --vspec-meta vspec_lookup.yaml
```

The YAML file maps FQNs to dictionaries of keys to overlay:

```yaml
Vehicle.Body.Mirrors:
  type: branch
  instances: ["DriverSide", "PassengerSide"]
  comment: Inherited from VSS 5.0

Vehicle.Body.Mirrors.Pan:
  type: sensor
  unit: percent
```

In vspec-meta mode the following additional behaviour is enabled:

- `"type"` is added to every branch node — derived from `@vspec(element: ...)` on the GraphQL type itself (e.g. `branch`, `struct`), falling back to `"branch"` if absent. The YAML overlay can still override it.
- Fields with `@vspec(fqn: ...)` have their output key renamed to the last segment of the FQN
- Enum fields annotated with `@vspec` gain an `"allowed"` list from the enum values
- All YAML keys for a matching FQN entry are merged into the node, with the YAML taking precedence
- Fields referencing a `@vspec(element: STRUCT)` type are exported as **leaf nodes** whose `datatype` is the struct's FQN (e.g. `VehicleDataTypes.TestBranch1.NestedStruct`) rather than expanded branch nodes
- If the YAML contains a `ComplexDataTypes` key, its FQN-indexed entries are assembled into a nested `ComplexDataTypes` section in the output (see [VSS Struct Types](#vss-struct-types-vspec-meta-only) below)

#### Output Structure

Both modes share the same structural convention:

```json
{
  "<RootTypeName>": {
    "description": "...",
    "children": {
      "<fieldName>": {
        "description": "...",
        "datatype": "<ScalarOrEnumName>",
        "unit": "...",
        "min": 0,
        "max": 100,
        "deprecated": "..."
      },
      "<branchFieldName>": {
        "children": { ... },
        "description": "...",
        "instances": [["VAL1", "VAL2"], ...]
      }
    }
  }
}
```

Leaf node keys (written when the corresponding information is present in the schema):

| Key | Source |
|-----|--------|
| `description` | GraphQL field docstring |
| `datatype` | Scalar or enum type name (`Float`, `UInt8`, `GearPosition`, `String[]`, …) |
| `min` | `@range(min: …)` directive |
| `max` | `@range(max: …)` directive |
| `unit` | Field argument `unit` default value |
| `deprecated` | GraphQL `@deprecated` reason |

Branch node keys:

| Key | Source |
|-----|--------|
| `children` | Object type fields |
| `description` | GraphQL field docstring |
| `instances` | Enum dimensions of the `@instanceTag` type (default mode) or YAML overlay (vspec-meta mode) |
| `type` | vspec-meta mode only — from `@vspec(element: ...)` on the type (e.g. `branch`, `struct`), or YAML overlay |
| `comment` | vspec-meta mode only — from YAML entry |

#### Examples

#### VSS Struct Types (vspec-meta only)

When a GraphQL schema contains `@vspec(element: STRUCT)` types (representing VSS struct datatypes), vspec-meta mode handles them differently from regular branch types:

- **Fields referencing a struct type become leaf nodes** — the field is not expanded into a branch; instead it gets a `datatype` equal to the struct's FQN as recorded in `@vspec(fqn: ...)` on the struct type. A `[]` suffix is appended for list fields.
- **Struct types are excluded from the main export** — they do not appear as top-level keys alongside signal branches.
- **A `ComplexDataTypes` section is built from the YAML** — when the `--vspec-meta` YAML contains a `ComplexDataTypes` key, its FQN-indexed entries are assembled into a nested hierarchy and added to the output as `result["ComplexDataTypes"]`.

Example YAML with a `ComplexDataTypes` section:

```yaml
A:
  description: Branch A.
  type: branch

A.NestedStructSensor:
  datatype: VehicleDataTypes.TestBranch1.NestedStruct
  description: A rich sensor with user-defined data type.
  type: sensor

ComplexDataTypes:
  VehicleDataTypes:
    description: Top-level branch for vehicle data types.
    type: branch
  VehicleDataTypes.TestBranch1:
    description: Test branch with structs and properties definitions
    type: branch
  VehicleDataTypes.TestBranch1.NestedStruct:
    description: A struct - Nested
    type: struct
  VehicleDataTypes.TestBranch1.NestedStruct.x:
    datatype: double
    description: x property
    min: -10
    type: property
```

Produces:

```json
{
  "A": {
    "children": {
      "NestedStructSensor": {
        "description": "A rich sensor with user-defined data type.",
        "datatype": "VehicleDataTypes.TestBranch1.NestedStruct",
        "type": "sensor"
      }
    },
    "description": "Branch A.",
    "type": "branch"
  },
  "ComplexDataTypes": {
    "VehicleDataTypes": {
      "description": "Top-level branch for vehicle data types.",
      "type": "branch",
      "children": {
        "TestBranch1": {
          "description": "Test branch with structs and properties definitions",
          "type": "branch",
          "children": {
            "NestedStruct": {
              "description": "A struct - Nested",
              "type": "struct",
              "children": {
                "x": {
                  "datatype": "double",
                  "description": "x property",
                  "min": -10,
                  "type": "property"
                }
              }
            }
          }
        }
      }
    }
  }
}
```

> **Default mode (no `--vspec-meta`)**: `@vspec(element: STRUCT)` types are treated as plain branches and expanded inline. Fields referencing them are expanded as nested `children` rather than leaf nodes with a struct FQN datatype. Field names reflect the camelCase names in the GraphQL schema rather than the original VSS snake_case names.

#### Examples

##### Export a Root Type

```bash
s2dm export json -s schema.graphql -o vehicle.json -r Vehicle
```

##### Export with VSS Metadata Overlay

```bash
s2dm export json \
  -s schema.graphql \
  -o vehicle_vss.json \
  -r Vehicle \
  --vspec-meta vspec_lookup.yaml
```

##### Filter to a Subset of Fields

```bash
s2dm export json -s schema.graphql -o adas.json -q adas_query.graphql
```

For help:

```bash
s2dm export json --help
```

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
directive @instanceTag on OBJECT | FIELD_DEFINITION
directive @metadata(comment: String, vssType: String) on FIELD_DEFINITION | OBJECT

type Vehicle @metadata(comment: "Vehicle entity", vssType: "branch") {
    id: ID!
    door: Door!
}

type Door {
    locked: Boolean!
    inCabinArea: InCabinArea2x3 @instanceTag
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
        "door": {
          "additionalProperties": false,
          "properties": {
            "ROW1": {
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
            },
            "ROW2": {
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
          "type": "object"
        }
      },
      "type": "object",
      "$comment": "Vehicle entity",
      "x-metadata": {
        "vssType": "branch"
      },
      "required": [
        "id"
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
    }
  },
  "type": "object",
  "title": "GraphQL Schema",
  "description": "JSON Schema generated from GraphQL schema"
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
  id: ID!                       # Non-null
  description: String           # Nullable
  category: VehicleCategory     # Nullable enum
  doorsOptional: [Door]         # Nullable list of nullable doors
  doorsRequired: [Door]!        # Non-null list of nullable doors
  doors: [Door!]!               # Non-null list of non-null doors
}

type Door {
  id: ID!
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
  "type": "object",
  "title": "GraphQL Schema",
  "description": "JSON Schema generated from GraphQL schema"
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
  "type": "object",
  "title": "GraphQL Schema",
  "description": "JSON Schema generated from GraphQL schema"
}
```

##### Nullability Rules

| GraphQL Type          | Strict Mode JSON Schema                                          |
| --------------------- | ---------------------------------------------------------------- |
| `String`              | `{"type": ["string", "null"]}`                                   |
| `String!`             | `{"type": "string"}`                                             |
| `VehicleType` (enum)  | `{"oneOf": [{"$ref": "#/$defs/VehicleType"}, {"type": "null"}]}` |
| `VehicleType!` (enum) | `{"$ref": "#/$defs/VehicleType"}`                                |
| `[String]`            | Array and items both nullable                                    |
| `[String!]`           | Array nullable, items non-null                                   |
| `[String]!`           | Array non-null, items nullable                                   |
| `[String!]!`          | Array and items both non-null                                    |

You can call the help for usage reference:

```bash
s2dm export jsonschema --help
```

### LinkML

This exporter translates the given GraphQL schema to [LinkML](https://linkml.io/linkml/) schema format (`.yaml`).

#### Key Features

- **Complete GraphQL Type Support**: Handles scalars, objects, input objects, enums, unions, interfaces, and list fields
- **Selection Query**: Use `--selection-query` to filter exported types and fields
- **Root Type Filtering**: Use `--root-type` to export one type and its transitive dependencies
- **Naming Configuration**: Use `--naming-config` to transform names before export
- **Expanded Instance Tags**: Use `--expanded-instances` to replace instance-tag arrays with singular attributes annotated with resolved instance names
- **Explicit Schema Metadata**: Requires LinkML schema identity and namespace inputs (`--id`, `--name`, `--default-prefix`, `--default-prefix-url`)

#### Usage

```bash
s2dm export linkml \
  --schema schema.graphql \
  --output schema.yaml \
  --id https://covesa.global/s2dm \
  --name VehicleSchema \
  --default-prefix s2dm \
  --default-prefix-url https://covesa.global/s2dm
```

#### Required Options

- `--schema, -s`: GraphQL schema file, directory, or URL (repeatable)
- `--output, -o`: Output file path (`.yaml`)
- `--id, -i`: LinkML schema identifier
- `--name, -n`: LinkML schema name
- `--default-prefix`: LinkML default prefix label
- `--default-prefix-url`: Namespace URI for `--default-prefix`

#### Example Transformation

Consider the following GraphQL schema:

```graphql
type Query {
  vehicle: Vehicle
}

enum FuelType {
  GASOLINE
  ELECTRIC
}

type Vehicle {
  id: ID!
  make: String!
  year: Int
  fuelType: FuelType
}
```

The LinkML exporter produces:

```yaml
name: VehicleSchema
id: https://covesa.global/s2dm
imports:
  - linkml:types
prefixes:
  linkml: https://w3id.org/linkml/
  s2dm: https://covesa.global/s2dm
default_prefix: s2dm
default_range: string
enums:
  FuelType:
    permissible_values:
      ELECTRIC: {}
      GASOLINE: {}
classes:
  Vehicle:
    attributes:
      id:
        identifier: true
        range: string
        required: true
      make:
        range: string
        required: true
      year:
        range: integer
      fuelType:
        range: FuelType
    tree_root: true
```

#### Type Mappings

GraphQL scalar types are mapped to LinkML ranges as follows:

| GraphQL Type | LinkML Range |
| ------------ | ------------ |
| `String`     | `string`     |
| `Int`        | `integer`    |
| `Float`      | `float`      |
| `Boolean`    | `boolean`    |
| `ID`         | `string`     |
| `Int8`       | `integer`    |
| `UInt8`      | `integer`    |
| `Int16`      | `integer`    |
| `UInt16`     | `integer`    |
| `UInt32`     | `integer`    |
| `Int64`      | `integer`    |
| `UInt64`     | `integer`    |

Additional type behavior:

- **Enums**: Converted to LinkML enums with `permissible_values`
- **Lists**: Converted to `multivalued: true`
- **Non-null fields**: Converted to `required: true`
- **Input objects**: Exported as LinkML classes with attributes
- **Unions**: Converted to `any_of` ranges
- **Interfaces**: Converted to abstract classes; implementing types map to `is_a`/`mixins`
- **Custom scalars**: Exported as LinkML types with `base: string`

The exporter skips GraphQL root/introspection types and intermediate expansion types.

#### Directive Support

S2DM directives are converted to LinkML constraints and annotations:

- `@range(min, max)` on output/input fields -> `minimum_value`, `maximum_value`
- `@cardinality(min, max)` on output/input fields -> `minimum_cardinality`, `maximum_cardinality`
- `@noDuplicates` on list fields -> `list_elements_unique: true`
- List item non-null (`[Type!]` / `[Type!]!`) -> `annotations.s2dm_list_item_required: "true"`
- `@metadata(...)` on object/interface/input object types and output/input fields -> LinkML annotations (`s2dm_metadata_*` keys)

You can call the help for usage reference:

```bash
s2dm export linkml --help
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
  doorPosition: DoorPosition @instanceTag
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
      doorPosition {
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

extend google.protobuf.MessageOptions {
  string message_source = 50001;
}

message RowEnum {
  option (message_source) = "RowEnum";

  enum Enum {
    ROWENUM_UNSPECIFIED = 0;
    ROW1 = 1;
    ROW2 = 2;
  }
}
message SideEnum {
  option (message_source) = "SideEnum";

  enum Enum {
    SIDEENUM_UNSPECIFIED = 0;
    DRIVERSIDE = 1;
    PASSENGERSIDE = 2;
  }
}

message Cabin {
  option (message_source) = "Cabin";

  repeated Door doors = 1;
  optional float temperature = 2;
}

message Door {
  option (message_source) = "Door";

  optional bool isLocked = 1;
  optional DoorPosition doorPosition = 2;
}

message DoorPosition {
  option (message_source) = "DoorPosition";

  optional RowEnum.Enum row = 1;
  optional SideEnum.Enum side = 2;
}

message Selection {
  option (message_source) = "query: Selection";

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
  string message_source = 50001;
}

extend google.protobuf.FieldOptions {
  string field_source = 50002;
}

message Selection {
  option (message_source) = "query: Selection";

  optional bool Vehicle_adas_abs_isEngaged = 1 [(field_source) = "ABS"];
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
  doorPosition: DoorPosition @instanceTag
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
      doorPosition {
        row
        side
      }
    }
  }
}
```

Default output uses repeated fields and includes the doorPosition field:

```protobuf
syntax = "proto3";

import "google/protobuf/descriptor.proto";

extend google.protobuf.MessageOptions {
  string message_source = 50001;
}

message RowEnum {
  option (message_source) = "RowEnum";

  enum Enum {
    ROWENUM_UNSPECIFIED = 0;
    ROW1 = 1;
    ROW2 = 2;
  }
}
message SideEnum {
  option (message_source) = "SideEnum";

  enum Enum {
    SIDEENUM_UNSPECIFIED = 0;
    DRIVERSIDE = 1;
    PASSENGERSIDE = 2;
  }
}

message Cabin {
  option (message_source) = "Cabin";

  repeated Door doors = 1;
}

message Door {
  option (message_source) = "Door";

  optional bool isLocked = 1;
  optional DoorPosition doorPosition = 2;
}

message DoorPosition {
  option (message_source) = "DoorPosition";

  optional RowEnum.Enum row = 1;
  optional SideEnum.Enum side = 2;
}

message Selection {
  option (message_source) = "query: Selection";

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
  string message_source = 50001;
}

message RowEnum {
  option (message_source) = "RowEnum";

  enum Enum {
    ROWENUM_UNSPECIFIED = 0;
    ROW1 = 1;
    ROW2 = 2;
  }
}

message SideEnum {
  option (message_source) = "SideEnum";

  enum Enum {
    SIDEENUM_UNSPECIFIED = 0;
    DRIVERSIDE = 1;
    PASSENGERSIDE = 2;
  }
}

message Cabin {
  option (message_source) = "Cabin";

  Door_Row Door = 1 [(buf.validate.field).required = true];
}

message Door {
  option (message_source) = "Door";

  optional bool isLocked = 1;
}

message Selection {
  option (message_source) = "query: Selection";

  optional Cabin cabin = 1;
}

message Door_Side {
  option (message_source) = "Door_Side";

  optional Door DRIVERSIDE = 1;
  optional Door PASSENGERSIDE = 2;
}

message Door_Row {
  option (message_source) = "Door_Row";

  Door_Side ROW1 = 1 [(buf.validate.field).required = true];
  Door_Side ROW2 = 2 [(buf.validate.field).required = true];
}
```

**Key differences:**

- Instance tag enums (`RowEnum`, `SideEnum`) remain in the output
- Types with `@instanceTag` directive (`DoorPosition`) are excluded from the output
- The `doorPosition` field is excluded from the Door message
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
  string message_source = 50001;
}

message Vehicle {
  option (message_source) = "Vehicle";

  optional int32 speed = 1 [(buf.validate.field).int32 = {gte: 0, lte: 300}];
  repeated string tags = 2 [(buf.validate.field).repeated = {unique: true, min_items: 1, max_items: 10}];
}

message Selection {
  option (message_source) = "query: Selection";

  optional Vehicle vehicle = 1;
}
```

#### Type Mappings

GraphQL types are mapped to protobuf types as follows:

| GraphQL Type | Protobuf Type |
| ------------ | ------------- |
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
  option (message_source) = "User";

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

### Apache Avro

The Avro exporter group provides two commands for exporting GraphQL schemas to [Apache Avro](https://avro.apache.org/) formats:

- **`s2dm export avro schema`**: Exports to Avro schema format (`.avsc`) using a selection query
- **`s2dm export avro protocol`**: Exports to Avro protocol format (`.avdl`) for types marked with the `@vspec(element: STRUCT)` directive

#### Common Features

Both exporters share the following features:

- **Complete GraphQL Type Support**: Handles all GraphQL types including scalars, objects, enums, unions, interfaces, and lists
- **Type Optimization**: Automatically optimizes integer types based on `@range` directive constraints
- **Namespace Support**: Use the `--namespace` flag to specify an Avro namespace for type references
- **Expanded Instance Tags**: Use the `--expanded-instances` flag to transform instance tag arrays into nested record structures

#### Avro Schema (`s2dm export avro schema`)

This exporter translates the given GraphQL schema to Avro schema format.

##### Selection Query (Required)

The Avro schema exporter requires a selection query to determine which types and fields to export:

```bash
s2dm export avro schema --schema schema.graphql --selection-query query.graphql --namespace com.example --output schema.avsc
```

See the [Selection Query Filtering](#selection-query-filtering) section for details on how selection queries work.

##### Example Transformation

Consider the following GraphQL schema and selection query:

GraphQL Schema:

```graphql
type Vehicle {
  id: ID!
  speed: Int
  doors: [Door]
}

type Door {
  isLocked: Boolean
}

enum Status {
  ACTIVE
  INACTIVE
}

type Query {
  vehicle: Vehicle
}
```

Selection Query:

```graphql
query VehicleData {
  vehicle {
    id
    speed
    doors {
      isLocked
    }
  }
}
```

The Avro schema exporter produces:

```bash
s2dm export avro schema --schema schema.graphql --selection-query query.graphql --namespace com.example --output vehicle.avsc
```

```json
{
  "type": "record",
  "name": "VehicleData",
  "namespace": "com.example",
  "fields": [
    {
      "name": "vehicle",
      "type": [
        "null",
        {
          "type": "record",
          "name": "Vehicle",
          "namespace": "com.example",
          "fields": [
            {
              "name": "id",
              "type": "string"
            },
            {
              "name": "speed",
              "type": ["null", "int"]
            },
            {
              "name": "doors",
              "type": [
                "null",
                {
                  "type": "array",
                  "items": [
                    "null",
                    {
                      "type": "record",
                      "name": "Door",
                      "namespace": "com.example",
                      "fields": [
                        {
                          "name": "isLocked",
                          "type": ["null", "boolean"]
                        }
                      ]
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

#### Avro protocol (`s2dm export avro protocol`)

This exporter generates Avro protocol protocol files (`.avdl`) for types marked with the `@vspec(element: STRUCT)` directive. Each type generates a separate protocol file containing the type and its dependencies.

##### Usage

```bash
s2dm export avro protocol --schema schema.graphql --namespace com.example --output ./output-directory
```

The command creates one `.avdl` file per struct type in the output directory.

##### Example

Given a GraphQL schema:

```graphql
directive @vspec(element: VspecElement!) on OBJECT

enum VspecElement {
  STRUCT
}

enum Status {
  ACTIVE
  INACTIVE
}

type Vehicle @vspec(element: STRUCT) {
  id: ID!
  make: String!
  status: Status
}

type Person {
  name: String
}

type Query {
  vehicle: Vehicle
  person: Person
}
```

The protocol exporter generates `Vehicle.avdl`:

```avro
@namespace("com.example")
protocol Vehicle {
  record Vehicle {
    string? id;
    string? make;
    string? status; /* enum Status */
  }
}
```

##### Strict Mode

Use the `--strict` flag to enforce strict type translation:

```bash
s2dm export avro protocol --schema schema.graphql --namespace com.example --output ./output-dir --strict
```

**Default behavior (without `--strict`):**

- Enum types are mapped to `string?`
- All fields are optional (use `?` suffix)
- Enum definitions are not included in the protocol

**Strict mode (with `--strict`):**

- Enum types are mapped to actual Avro enum types
- Nullability is enforced from GraphQL schema (non-null fields without `?`)
- Enum definitions are included in the protocol

Example with strict mode:

```graphql
type Vehicle @vspec(element: STRUCT) {
  id: ID!
  status: Status
}

enum Status {
  ACTIVE
  INACTIVE
}
```

Generates:

```avro
@namespace("com.example")
protocol Vehicle {
  enum Status { ACTIVE, INACTIVE }
  record Vehicle {
    string id;
    Status? status;
  }
}
```

##### Per-Type Namespaces

After the tools collects types mapped with the `@vspec` directive, it scans the directive annotation for an optional `metadata` parameter, which you can utilize to specify a custom namespace for individual types using a key-value pair. If not provided, the global namespace from the `--namespace` flag is used.

```graphql
directive @vspec(element: VspecElement!, metadata: [KeyValue]) on OBJECT

input KeyValue {
  key: String!
  value: String!
}

enum VspecElement {
  STRUCT
}

type Vehicle @vspec(element: STRUCT, metadata: [{key: "namespace", value: "com.vehicle"}]) {
  id: ID!
  make: String!
}

type Person @vspec(element: STRUCT) {
  name: String!
}
```

Generates:

**Vehicle.avdl:**

```avro
@namespace("com.vehicle")
protocol Vehicle {
  record Vehicle {
    string? id;
    string? make;
  }
}
```

**Person.avdl:**

```avro
@namespace("com.example")
protocol Person {
  record Person {
    string? name;
  }
}
```

##### Help

```bash
s2dm export avro protocol --help
```

#### Type Mappings

##### Scalar Types

GraphQL scalar types are mapped to Avro types (same for both exporters):

| GraphQL Type | Avro Type |
| ------------ | --------- |
| `String`     | `string`  |
| `Int`        | `int`     |
| `Float`      | `double`  |
| `Boolean`    | `boolean` |
| `ID`         | `string`  |
| `Int8`       | `int`     |
| `UInt8`      | `int`     |
| `Int16`      | `int`     |
| `UInt16`     | `int`     |
| `UInt32`     | `long`    |
| `Int64`      | `long`    |
| `UInt64`     | `long`    |

##### List Types

**Avro Schema (`.avsc`):**

- `[String]` → `{"type": "array", "items": ["null", "string"]}`
- `[String!]` → `{"type": "array", "items": "string"}`
- `[String]!` → `{"type": "array", "items": ["null", "string"]}`
- `[String!]!` → `{"type": "array", "items": "string"}`

**Avro protocol (`.avdl`):**

Non-strict mode (default):

- All list fields → `array<type>?`

Strict mode:

- `[String]` (nullable list) → `array<string>?`
- `[String]!` (non-null list) → `array<string>`

##### Enum Types

**Avro Schema (`.avsc`):**

```json
{
  "type": "enum",
  "name": "Status",
  "namespace": "com.example",
  "symbols": ["ACTIVE", "INACTIVE"]
}
```

**Avro protocol (`.avdl`):**

Non-strict mode (default):

- Enums are mapped to `string` type

Strict mode:

```avro
enum Status {
  ACTIVE,
  INACTIVE
}
```

##### Field Nullability

**Avro Schema (`.avsc`):**

- **Nullable fields** (`name: String`) → `["null", "string"]`
- **Non-nullable fields** (`id: ID!`) → `"string"`

**Avro protocol (`.avdl`):**

Non-strict mode (default):

- All fields → `string?` (always optional)

Strict mode:

- **Nullable fields** (`name: String`) → `string?`
- **Non-nullable fields** (`id: ID!`) → `string`

##### Range Directive Optimization

The `@range` directive automatically optimizes integer type selection between `int` and `long` for both exporters:

```graphql
directive @range(min: Float, max: Float) on FIELD_DEFINITION
directive @vspec(element: VspecElement!) on OBJECT

enum VspecElement {
  STRUCT
}

type Sensor @vspec(element: STRUCT) {
  temperature: Int64 @range(min: -40, max: 150)
  mileage: Int @range(min: 0, max: 5000000000)
}
```

**Avro Schema (`.avsc`) produces:**

```json
{
  "type": "record",
  "name": "Sensor",
  "namespace": "com.example",
  "fields": [
    {
      "name": "temperature",
      "type": ["null", "int"]
    },
    {
      "name": "mileage",
      "type": ["null", "long"]
    }
  ]
}
```

**Avro protocol (`.avdl`) produces:**

```avro
@namespace("com.example")
protocol Sensor {
  record Sensor {
    int? temperature;
    long? mileage;
  }
}
```

**Optimization rules:**

- If all specified range bounds fit in 32-bit signed range (-2³¹ to 2³¹-1), use `int`
- If any bound exceeds 32-bit range, use `long`
- Works with partial ranges: `@range(min: 0)` or `@range(max: 100)`
- Without `@range`, uses default type mapping

You can call the help for usage reference:

```bash
s2dm export avro schema --help
s2dm export avro protocol --help
```

## Insights Commands

The `insights` command group analyzes GraphQL schemas and prints compact JSON summaries. These outputs are aligned with the summary cards in the playground, not the detailed drill-down views.

### Shared Schema Input

All `insights` subcommands require at least one schema input:

- `-s, --schema PATH`: GraphQL schema file, directory, or URL. Can be specified multiple times.

#### Shared Usage Pattern

```bash
s2dm insights <subcommand> -s <schema_path>
```

#### Shared Examples

Single file:

```bash
s2dm insights concepts -s schema.graphql
```

Directory of schemas:

```bash
s2dm insights quality -s ./spec/
```

Multiple schema inputs:

```bash
s2dm insights relationships -s ./spec/core -s ./spec/extensions.graphql
```

Remote schema URL:

```bash
s2dm insights quality -s https://example.org/schema.graphql
```

### Example Schema

The examples below use a standalone schema assembled from GraphQL snippets already shown elsewhere on this page. The `@instanceTag` directive definition comes from the JSON Schema example, and the `Cabin`/`Door`/`DoorPosition` structure comes from the Protobuf example.

```graphql
directive @instanceTag on OBJECT

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

### Concepts

The `insights concepts` command prints a compact composition summary.

#### Usage

```bash
s2dm insights concepts -s schema.graphql
```

#### What It Prints

- `field_container_types`: Object, interface, and input type totals
- `fields`: Total, leaf-field, and relationship-field counts
- `enums`: Enum totals and enum-value statistics
- `scalars`: Built-in versus custom scalar usage totals
- `enum_usage`: Used versus unused enum counts

#### Example

```bash
uv run s2dm insights concepts -s schema.graphql
```

#### Example Output

```text
{
  "field_container_types": {
    "total": 4,
    "object_types": 4,
    "interface_types": 0,
    "input_types": 0
  },
  "fields": {
    "total": 7,
    "leaf_fields": 4,
    "relationship_fields": 3
  },
  "enums": {
    "total": 2,
    "enum_values": 4,
    "median_values_per_enum": 2.0
  },
  "scalars": {
    "total": 2,
    "built_in": 2,
    "custom": 0
  },
  "enum_usage": {
    "used": 2,
    "unused": 0,
    "total": 2
  }
}
```

In this example, `Cabin.doors`, `Door.instanceTag`, and `Query.cabin` are counted as relationship fields, while `Cabin.temperature`, `Door.isLocked`, `DoorPosition.row`, and `DoorPosition.side` are counted as leaf fields.

### Relationships

The `insights relationships` command prints a compact relationships summary.

#### Usage

```bash
s2dm insights relationships -s schema.graphql
```

#### What It Prints

- `references_count`: Referenced-type totals plus most-referenced, least-referenced, and top-reference previews
- `deepest_nested_paths`: Maximum depth, how many paths have that maximum depth, depth distribution, and one example deepest path
- `cyclic_references`: Cycle totals, cycle-length distribution, and one example shortest cycle

#### Example

```bash
uv run s2dm insights relationships -s schema.graphql
```

#### Example Output

```text
{
  "references_count": {
    "referenced": 3,
    "total_references": 3,
    "unused": 1,
    "most_referenced": {
      "name": "Seat",
      "count": 1
    },
    "least_referenced": {
      "name": "Vehicle",
      "count": 1
    },
    "top_references": [
      {
        "name": "Seat",
        "count": 1
      },
      {
        "name": "SeatTag",
        "count": 1
      },
      {
        "name": "Vehicle",
        "count": 1
      }
    ]
  },
  "deepest_nested_paths": {
    "max_depth": 2,
    "paths_with_max_depth_count": 1,
    "total_paths": 1,
    "depth_distribution": [
      {
        "depth": 2,
        "path_count": 1
      }
    ],
    "deepest_path_example": {
      "depth": 2,
      "path": [
        "Vehicle",
        "seat: Seat",
        "tag: SeatTag"
      ]
    }
  },
  "cyclic_references": {
    "count": 0,
    "shortest_length": 0,
    "cycle_length_distribution": [],
    "shortest_cycle_example": null
  }
}
```

In this example, the deepest reachable object-reference path is `Vehicle -> Seat -> SeatTag`, which gives a maximum depth of `2`. There are no cycles, so `cycle_length_distribution` is empty and `shortest_cycle_example` is `null`.

### Quality

The `insights quality` command prints the compact quality summary categories highlighted in the playground, including documentation coverage.

#### Usage

```bash
s2dm insights quality -s schema.graphql
```

#### What It Prints

- `coverage`: Per-category documentation totals, documented counts, undocumented counts, and percentages
- `unused_elements`: Top-level used-versus-unused totals plus grouped summaries under `categories.types`, `categories.enums`, and `categories.directives`
- `missing_units`: The number of scalar fields that declare no unit

#### Example

```bash
uv run s2dm insights quality -s schema.graphql
```

#### Example Output

```text
{
  "coverage": {
    "types": {
      "total": 4,
      "documented": 0,
      "undocumented": 4,
      "percentage": 0
    },
    "fields": {
      "total": 7,
      "documented": 0,
      "undocumented": 7,
      "percentage": 0
    },
    "enums": {
      "total": 2,
      "documented": 0,
      "undocumented": 2,
      "percentage": 0
    },
    "enum_values": {
      "total": 4,
      "documented": 0,
      "undocumented": 4,
      "percentage": 0
    },
    "directives": {
      "total": 1,
      "documented": 0,
      "undocumented": 1,
      "percentage": 0
    }
  },
  "unused_elements": {
    "total": 7,
    "used": 7,
    "unused": 0,
    "percentage": 0,
    "categories": {
      "types": {
        "total": 4,
        "used": 4,
        "unused": 0,
        "percentage": 0
      },
      "enums": {
        "total": 2,
        "used": 2,
        "unused": 0,
        "percentage": 0
      },
      "directives": {
        "total": 1,
        "used": 1,
        "unused": 0,
        "percentage": 0
      }
    }
  },
  "missing_units": {
    "count": 1
  }
}
```

In this example schema, nothing is unused, so `unused_elements.used` equals `unused_elements.total` and every unused percentage is `0`.

The `missing_units.count` value is `1` because `Cabin.temperature` is a scalar field that does not declare a `unit` argument.

## Playground Commands

The playground commands initialize and run the local S2DM GUI playground.

### Init

The `playground init` command installs playground dependencies and builds the frontend application.

#### Usage

```bash
s2dm playground init
```

#### Behavior

- Validates that the `playground/` directory exists.
- Validates that `playground/package.json` exists.
- Runs `npm install` in `playground/`.
- Runs `npm run build` in `playground/`.

#### Example

```bash
s2dm playground init
```

### Start

The `playground start` command starts the local API and frontend servers, then opens the playground in your default browser.

#### Usage

```bash
s2dm playground start
```

#### Behavior

- Validates that the `playground/` directory exists.
- Validates that `playground/node_modules/` exists (run `s2dm playground init` first).
- Allocates free local ports for the API server and React dev server.
- Starts FastAPI with `uvicorn s2dm.api.main:app --reload`.
- Starts the React dev server with `npm run dev -- --port <port> --strictPort`.
- Sets `VITE_API_BASE_URL` for the frontend process.
- Opens the default browser at the selected React URL.
- Streams logs for both servers until interrupted.
- On `Ctrl+C`, terminates both processes gracefully.

#### Example

```bash
s2dm playground start
```

## Export RDF

The `export rdf` command materializes a GraphQL schema as RDF triples using the s2dm ontology. It produces two separate graphs: a SKOS graph (concepts, collections, labels) and a data graph (ontology instantiation). Both can be queried with SPARQL.

#### Usage

```bash
s2dm export rdf -s <schema_path> -o <output_dir> --namespace <uri>
```

#### Options

- `-s, --schema PATH`: GraphQL schema file, directory, or URL (required, can be specified multiple times)
- `-o, --output DIR`: Output directory for RDF artifacts (required)
- `--namespace URI`: Namespace URI for concept URIs (required)
- `--prefix TEXT`: Prefix for concept URIs (default: `ns`)
- `--language TEXT`: BCP 47 language tag for prefLabels (default: `en`)
- `--output-formats TEXT`: Comma-separated output formats (default: `nt,turtle`). Supported: `json-ld` (or `jsonld`), `nt`, `turtle` (or `ttl`)

#### Output Files

Produces two pairs of files in the output directory (formats configurable via `--output-formats`):

- **skos.{nt,ttl,...}** – SKOS concepts, collections, and prefLabels
- **data_graph.{nt,ttl,...}** – s2dm ontology instantiation (ObjectType, Field, hasField, etc.)

For SPARQL queries that traverse the schema structure, use `data_graph.nt` or `data_graph.ttl`.

#### Examples

Generate sorted n-triples and Turtle (default):

```bash
s2dm export rdf \
  -s spec/ \
  -o ./rdf-output \
  --namespace "https://covesa.org/s2dm/mydomain#"
```

Generate all formats including JSON-LD (for releases):

```bash
s2dm export rdf \
  -s spec/ \
  -o ./rdf-output \
  --namespace "https://covesa.org/s2dm/mydomain#" \
  --output-formats nt,turtle,json-ld
```

Generate only n-triples (for git):

```bash
s2dm export rdf \
  -s spec/ \
  -o ./rdf-output \
  --namespace "https://covesa.org/s2dm/mydomain#" \
  --output-formats nt
```

#### Output Formats

| Format    | Alias    | Extension | Description                                          |
| --------- | -------- | --------- | ---------------------------------------------------- |
| `nt`      |          | `.nt`     | Sorted n-triples (deterministic, git-friendly diffs) |
| `turtle`  | `ttl`    | `.ttl`    | Turtle (human-readable, for consumption)             |
| `json-ld` | `jsonld` | `.jsonld` | JSON-LD (for web and linked data tooling)            |

The `nt` format is special-cased to produce lexicographically sorted lines, ensuring deterministic output suitable for version control.

#### Ontology Mapping

The s2dm ontology maps GraphQL SDL elements to RDF as follows:

- **Object types**: `rdf:type skos:Concept, s2dm:ObjectType`
- **Fields**: `rdf:type skos:Concept, s2dm:Field` with `s2dm:hasOutputType` and `s2dm:usesTypeWrapperPattern`
- **Enum types**: `rdf:type skos:Concept, s2dm:EnumType` with `s2dm:hasEnumValue`
- **Enum values**: `rdf:type skos:Concept, s2dm:EnumValue`
- **Interface types**: `rdf:type skos:Concept, s2dm:InterfaceType`
- **Input object types**: `rdf:type skos:Concept, s2dm:InputObjectType`
- **Union types**: `rdf:type skos:Concept, s2dm:UnionType` with `s2dm:hasUnionMember`
- **Built-in scalars**: `s2dm:Int`, `s2dm:Float`, `s2dm:String`, `s2dm:Boolean`, `s2dm:ID`

## Query Commands

The `query` command group provides predefined SPARQL queries for traversing and analysing an RDF-materialized schema. Each command can either load pre-generated RDF files or materialize on-the-fly from a GraphQL schema.

### Input Options (shared by all query commands)

Provide **one** of the following for the RDF graph:

- `--rdf PATH`: Pre-generated RDF file, directory, or URL. Can be specified multiple times. Supported formats: `.nt`, `.ttl`, `.jsonld`. Directories are recursively scanned for matching files; URLs are downloaded to a temp file.
- `-s, --schema PATH` + `--namespace URI`: Materialize from GraphQL schema on-the-fly

Specify the query with **one** of:

- `QUERY_NAME`: A predefined query from the builtin registry (see below)
- `--query-file PATH` / `-q PATH`: Path to a custom `.sparql` file

Additional option:

- `--json`: Output results as JSON instead of a table

### Builtin Query Registry

Predefined queries are loaded from `*.sparql` files in the `sparql_queries/` directory within the s2dm package. Each file stem (e.g. `fields-outputting-enum`) becomes the query name. Run `s2dm query --help` to see the full list.

### fields-outputting-enum

Find all fields whose output type is an enum type.

```bash
# From a pre-generated file (use data_graph.nt for ontology queries)
s2dm query fields-outputting-enum --rdf output/data_graph.nt

# From multiple RDF files (graphs are merged)
s2dm query fields-outputting-enum --rdf output/data_graph.nt --rdf other/skos.nt

# From a directory (all .nt, .ttl, .jsonld files inside are loaded)
s2dm query fields-outputting-enum --rdf output/

# From a URL
s2dm query fields-outputting-enum --rdf https://example.org/ontology/data_graph.ttl

# From a GraphQL schema (on-the-fly materialization)
s2dm query fields-outputting-enum -s spec/ --namespace "https://example.org/#"

# Custom SPARQL file
s2dm query --query-file my_query.sparql --rdf output/data_graph.nt

# JSON output
s2dm query fields-outputting-enum --rdf output/data_graph.nt --json
```

**Example output:**

```
             fields-outputting-enum
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
┃ field                 ┃ enumType              ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
│ Cabin.kind            │ CabinKindEnum         │
│ InCabinArea2x2.column │ TwoColumnsInCabinEnum │
│ InCabinArea2x2.row    │ TwoRowsInCabinEnum    │
└───────────────────────┴───────────────────────┘
```

### object-types-with-fields

List all object types and their fields.

```bash
s2dm query object-types-with-fields --rdf output/data_graph.nt
```

**Example output:**

```
         object-types-with-fields
┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┓
┃ objectType     ┃ field                 ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━┩
│ Cabin          │ Cabin.doors           │
│ Cabin          │ Cabin.kind            │
│ Door           │ Door.isOpen           │
│ Door           │ Door.window           │
│ Window         │ Window.isTinted       │
└────────────────┴───────────────────────┘
```

### list-type-fields

Find all fields that use a list-like type wrapper pattern (`list`, `nonNullList`, `listOfNonNull`, `nonNullListOfNonNull`).

```bash
s2dm query list-type-fields --rdf output/data_graph.nt --json
```

**Example JSON output:**

```json
[
  {
    "field": "https://example.org/my-domain#Cabin.doors",
    "pattern": "https://covesa.global/models/s2dm#list"
  }
]
```

## Common Features

### Path Resolution

Commands that accept `-s, --schema` or `--rdf` use a unified path resolver that supports:

- **Files**: A single file path (e.g. `schema.graphql`, `data_graph.nt`)
- **Directories**: Recursively resolved to matching files (e.g. `spec/` → all `.graphql` files; `output/` → all `.nt`, `.ttl`, `.jsonld` for RDF)
- **URLs**: HTTP/HTTPS URLs are downloaded to a temporary file. The file extension is inferred from the URL path when multiple formats are supported (e.g. `.ttl` vs `.nt` for RDF).

Schema options accept `.graphql` files; RDF options accept `.nt`, `.ttl`, and `.jsonld`. Multiple paths can be specified; directories expand to a deduplicated, sorted file list.

### Selection Query Filtering

All export commands and the compose command support the `--selection-query` flag to filter the schema based on a GraphQL query. For Protobuf and Avro exporters, the selection query is required.

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

The naming configuration defines naming conventions for GraphQL schema elements using a YAML file. This configuration can be used for:

- **Transformation**: Converting element names to match desired conventions
- **Validation**: Checking that element names follow specified conventions

Commands that support `--naming-config`:

- `check constraints` - naming validation
- `compose` - naming transformation
- `export jsonschema` - naming transformation
- `export linkml` - naming transformation
- `export protobuf` - naming transformation
- `export shacl` - naming transformation
- `export vspec` - naming transformation

#### Configuration Format

The naming configuration is defined in a YAML file with the following structure:

```yaml
type:
  object: PascalCase
  interface: PascalCase
  input: PascalCase
  enum: PascalCase
  union: PascalCase
  scalar: PascalCase

field:
  object: camelCase
  interface: camelCase
  input: snake_case

enumValue: MACROCASE

instanceTag: COBOL-CASE

argument:
  field: camelCase
```

#### Supported Case Formats

The naming configuration supports the following case conversion formats:

- **camelCase**: `somePropertyName`
- **PascalCase**: `SomePropertyName`
- **snake_case**: `some_property_name`
- **kebab-case**: `some-property-name`
- **MACROCASE**: `SOME_PROPERTY_NAME`
- **COBOL-CASE**: `SOME-PROPERTY-NAME`
- **flatcase**: `somepropertyname`
- **TitleCase**: `Some Property Name`

#### Example

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
instanceTag: PascalCase   # Required for transformation if `enumValue` is defined.
```

For transformation, names are converted to match the configuration:

- Type: `vehicle_info` → `VehicleInfo`
- Field: `avg_speed` → `avgSpeed`
- Field: `fuel_type` → `fuelType`
- Enum type: `fuel_type_enum` → `FuelTypeEnum`
- Enum values: `GASOLINE_TYPE` → `GasolineType`, `DIESEL_TYPE` → `DieselType`

For validation, the schema is checked against the configuration:

- `vehicle_info` fails (expected PascalCase)
- `avg_speed` fails (expected camelCase)
- `fuel_type` fails (expected camelCase)
- `fuel_type_enum` fails (expected PascalCase)
- `GASOLINE_TYPE` fails (expected PascalCase)

#### How `instanceTag` Naming Works

The `instanceTag` key gives enum values that are used inside an `@instanceTag` type their **own naming rule**, separate from the global `enumValue` rule.

Think of it this way: an `@instanceTag` type acts as an identification label for multiple instances of an entity (for example, which specific seat or door you are referring to). The enum values inside it serve as identifiers in that labelling scheme, and you may want them to follow a different convention than ordinary enum values elsewhere in the schema.

**The important rule to understand:** when you set `instanceTag` to a case format, that format is applied to the **enum type itself** — meaning every place that enum appears in the schema will use the new casing, not just inside the instance tag context. This is because the schema treats an enum as a single definition; its values cannot have two different names at the same time.

For example, given:

```graphql
enum TwoRows { FRONT  REAR }

type DoorTag @instanceTag {
  row: TwoRows
}

type SomeOtherType {
  preferredRow: TwoRows   # also uses TwoRows
}
```

With `instanceTag: PascalCase`, `TwoRows` values become `Front` and `Rear` **everywhere** — including in `SomeOtherType.preferredRow`.

**Practical recommendation:** If you want instance tag identifiers to follow a distinct case without affecting other parts of the schema, define dedicated enums that are used *exclusively* inside the `@instanceTag` type and nowhere else. That way, the `instanceTag` case change is isolated to those enums:

```graphql
# Used only inside @instanceTag — safe to give a different case
enum DoorRowTag { FRONT  REAR }
enum DoorSideTag { LEFT  RIGHT }

type DoorTag @instanceTag {
  row: DoorRowTag
  side: DoorSideTag
}

# Uses its own separate enum — unaffected by instanceTag naming
enum GeneralDirection { FRONT  REAR  LEFT  RIGHT }

type Navigation {
  heading: GeneralDirection
}
```

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

**Context-specific Rules:**

- **EnumValue-InstanceTag pairing**: If `enumValue` is present in the configuration for transformation commands, `instanceTag` must also be present.

#### Notes

- Built-in GraphQL types (`String`, `Int`, `Float`, `Boolean`, `ID`, `Query`, `Mutation`, `Subscription`) are never transformed.
- When an element type is not configured, it is neither transformed or nor validated.

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
directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

type Cabin {
  doors: [Door]
  mirrors: [Mirror]
}

type Door {
  isLocked: Boolean
  doorPosition: DoorPosition @instanceTag
}

type DoorPosition @instanceTag {
  row: RowEnum
  side: SideEnum
}

type Mirror {
  isFolded: Boolean
  position: MirrorPosition @instanceTag
}

enum MirrorPosition @instanceTag {
  LEFT
  CENTER
  RIGHT
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

An instance tag can be backed either by an object type (`DoorPosition`, whose enum fields form a multi-dimensional cartesian product) or directly by an enum (`MirrorPosition`, a single dimension marked with `@instanceTag` on the enum itself).

**Without `--expanded-instances` (default):**

The schema structure remains as-is with the list fields and the instance-tag fields (`doorPosition`, `position`) preserved.

**With `--expanded-instances`:**

The schema is transformed to use nested intermediate types:

```graphql
directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

type Cabin {
  Door: Door_Row!
  Mirror: Mirror_Position!
}

type Door {
  isLocked: Boolean
}

type Mirror {
  isFolded: Boolean
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

type Door_Side {
  DRIVERSIDE: Door
  PASSENGERSIDE: Door
}

type Door_Row {
  ROW1: Door_Side!
  ROW2: Door_Side!
}

type Mirror_Position {
  LEFT: Mirror
  CENTER: Mirror
  RIGHT: Mirror
}
```

#### Key Changes

- **Field names**: Plural list fields (`doors`, `mirrors`) are renamed to singular (`Door`, `Mirror`)
- **Field types**: List types (`[Door]`) become intermediate types (`Door_Row`)
- **Intermediate types**: New types are created representing the cartesian product of instance tag enums (`Door_Row`, `Door_Side`); an enum-backed tag is a single dimension, so it produces one intermediate type (`Mirror_Position`)
- **Instance tag removal**: The instance-tag fields (`doorPosition`, `position`) are removed from the base types (`Door`, `Mirror`)
- **Type removal**: Object types with the `@instanceTag` directive (`DoorPosition`) and enums marked with `@instanceTag` (`MirrorPosition`) are removed from the schema
- **Enum preservation**: Enums used as fields inside an `@instanceTag` object (`RowEnum`, `SideEnum`) remain in the schema

#### Excluding Instance Combinations

The `@instanceTag` directive accepts an optional `exclude` argument — a list of instance combinations that should be pruned from the expansion. Each entry is the dot-joined path of enum values for a single combination (for example `"ROW1.MIDDLE"`), in the same order as the fields of the `@instanceTag` type.

Use it when a particular combination does not exist in the modeled entity (for example, a vehicle whose front row has no middle seat):

```graphql
directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

type Cabin {
  seats: [Seat]
}

type Seat {
  isOccupied: Boolean
  seatPosition: SeatPosition @instanceTag(exclude: ["ROW1.MIDDLE"])
}

type SeatPosition @instanceTag {
  row: RowEnum
  position: PositionEnum
}

enum RowEnum {
  ROW1
  ROW2
}

enum PositionEnum {
  LEFT
  MIDDLE
  RIGHT
}

type Query {
  cabin: Cabin
}
```

Running the expansion:

```bash
s2dm compose -s schema.graphql --expanded-instances -o expanded.graphql
```

produces the following schema. The excluded `ROW1.MIDDLE` combination is dropped, so the two rows no longer share a single position type — `ROW1` only expands to `LEFT` and `RIGHT`, while `ROW2` retains all three positions:

```graphql
directive @instanceTag(exclude: [String!]) on OBJECT | FIELD_DEFINITION | ENUM

type Cabin {
  Seat: Seat_Row!
}

type Seat {
  isOccupied: Boolean
}

enum RowEnum {
  ROW1
  ROW2
}

enum PositionEnum {
  LEFT
  MIDDLE
  RIGHT
}

type Query {
  cabin: Cabin
}

type Seat_ROW1_Position {
  LEFT: Seat
  RIGHT: Seat
}

type Seat_ROW2_Position {
  LEFT: Seat
  MIDDLE: Seat
  RIGHT: Seat
}

type Seat_Row {
  ROW1: Seat_ROW1_Position!
  ROW2: Seat_ROW2_Position!
}
```

If an `exclude` entry matches no instance combination, the expansion fails with an error rather than silently ignoring it.
