# Tools
## Overview
### For data modelers
For a user who is working with a domain model specified with the `S2DM` approach, the Command Line Interface (CLI) is the way to go.
The CLI offers so far the following commands:
- [`export`](#export-command)
> TODO: Add and describe other commands once they are available.

### For `S2DM` developers
Developers can refer to other scripts available in this repository, such as:
- `utils`
- [Identifiers](#identifiers)
> TODO: Add and describe other useful tools or scripts once they are available.

### Composing an schema from modular files
Instead of modeling a huge monolithic model, GraphQL schemas can be specified in multiple small ones (aka., sub graphs).
Then, specific elements from different sub models can be stiched together to form the composed model with the structure needed.
To learn more about it, please refer to the [official documentation of the GraphQL Schema Definition Language](https://graphql.org/learn/federation/).

The general workflow looks like this:
```mermaid
graph LR
  subgraph Conceptual layer - S2DM
    source_file_1
    source_file_2
    source_file_N
    subgraph tools
      Composer
      Exporter
    end
  end
  subgraph Physical layer
    App_SHACL
    App_YAML
    App_JSON
  end
  source_file_1 --GraphQL schema 1--> Composer
  source_file_2 --GraphQL schema 2--> Composer
  source_file_N --GraphQL schema N--> Composer
  Composer --Merged GraphQL schema--> Exporter
  Exporter --SHACL--> App_SHACL
  Exporter --YAML--> App_YAML
  Exporter --JSON schema--> App_JSON
```
The tool can load multiple GraphQL schema files at once, as long as they are located in the same directory. This is currently done in the `utils` module with the [load function of the `Ariadne` package](https://ariadnegraphql.org/docs/modularization), which validates the syntax of every loaded file.
Therefore, it is possible to split a domain model into multiple smaller files. Such modularity is recommended to facilitate the further extension and maintenance of the domain model.
For example, in the figure shown above, schemas `1`, `2`, ..., `N` are merged into one before calling the exporter.



## export command
The exporter command parses the specified model and creates the artifact that is needed by the system in the physical layer.
```shell
s2dm export <some_supported_format> ...
```

#### Available exporters
The tools can currently export a given model into:
* [VSPEC](#vspec-exporter) - `tools/to_vspec.py`
* [SHACL](#shacl-exporter) - `tools/to_shacl.py`
* [JSON Schema](#json-schema-exporter) - `exporters/jsonschema/`

#### Supported field cases by exporter
> See `docs/MODELING_GUIDE.md` for more information on cases for fields and the custom directives, such as @noDuplicates.

| Case | `outputType`| VSPEC | SHACL| JSON Schema |
|----------|----------|----------|----------|----------|
| **Nullable Singular Field**   | `NamedType`   | ✅ | ✅ | ✅ |
| **Non-Nullable Singular Field**   | `NamedType!`   | ✅ | ✅ | ✅ |
| **Nullable List Field**   | `[NamedType]`   | ✅ | ❌ | ✅ |
| **Non-Nullable List Field**   | `[NamedType]!`   | ✅ | ❌ | ✅ |
| **Nullable List of Non-Nullable Elements**   | `[NamedType!]`   | ✅ | ❌ | ✅ |
| **Non-Nullable List of Non-Nullable Elements**   | `[NamedType!]!`   | ✅ | ❌ | ✅ |
| **Nullable Set Field**   | `[NamedType] @noDuplicates` | ❌ |✅ | ✅ |
| **Non-Nullable Set Field**   | `[NamedType]! @noDuplicates`   | ❌ |✅| ✅ |

### VSPEC exporter
This exporter translates the given GraphQL schema to the [Vehicle Signal Specification (VSS)](https://covesa.github.io/vehicle_signal_specification/) format (i.e., a YAML-like file with a custom syntax known as `VSPEC`).

For example, considering the following GraphQL schema:
```gql
type Vehicle {
  cabin: Cabin
}

type Cabin {
  seats: [Seat]
}

type Seat {
  instanceTag: InCabinArea2x2
  position(unit: Length_Unit_Enum = MILLIMETER): UInt16
    @metadata(vssType: "actuator")
}
```

It results in this `vspec`:
```yaml
Vehicle:
  description: ...
  type: branch

Vehicle.Cabin:
  description: ...
  type: branch

Vehicle.Cabin.Seat:
  description: ...
  instances:
  - [ROW1, ROW2]
  - [DRIVERSIDE, PASSENGERSIDE]
  type: branch

Vehicle.Cabin.Seat.position:
  datatype: uint16
  description: ...
  type: actuator
  unit: mm
```

For an extended example of this conversion, please see the [examples](examples/).

You can call the help for usage reference like this:
```bash
s2dm export vspec --help
```

### SHACL exporter
This exporter translates the given GraphQL schema to [SHACL](https://www.w3.org/TR/shacl/).

The [Shapes Constraint Language (SHACL)](https://www.w3.org/TR/shacl/) is a framework used to validate data in [Resource Description Framework (RDF)](https://www.w3.org/RDF/) format.
In other words, if you work with the RDF graph data model and triple stores (i.e., RDF-based graph databases), SHACL is used to validate a certain RDF data graph.
Think of it as a set of rules or criteria that your data needs to meet. If you're working with data that follows certain structures or patterns, SHACL helps make sure everything is in the right place and follows the right format. It's like having a checklist to ensure your data is accurate and consistent, making it easier to work with and understand. This is especially useful in fields like data management and semantic web technologies, where data integrity is crucial.

#### RDF in a nutshell
The core of RDF is a triple consisting of:
```mermaid
graph LR
  subject -- predicate --> object
```
So, an RDF data graph consists of a set of such triples. For example:
```mermaid
graph LR
  Max --a--> Person
```
```mermaid
graph LR
  Vehicle --hasOccupant--> Person
```
```mermaid
graph LR
  Max --a--> Person
```

Since every resource is uniquely identified in RDF, the set of triples resembles a graph.
Abstract concepts define the most generic `Terminology` (aka., `TBox`).
For example, `Person` and `Vehicle`.
More specific concepts constitute the `Categories` (aka., `CBox`) of a domain.
For example, `CarOccupant` and `Car`.
Finally, the actual data (aka., `ABox`) is connected to the upper concepts that provide context.
For example, `Max` and `BMW_X1`.

```mermaid
graph RL
  subgraph TBox
    Vehicle
    Person
  end
  subgraph CBox
    Car
    CarOccupant
  end
  subgraph ABox
    BMW_X1
    Max
  end

  Vehicle --hasOccupant--> Person
  CarOccupant --subClassOf--> Person
  Car --subClassOf--> Vehicle
  Max --a--> CarOccupant
  BMW_X1 --a--> Car
  BMW_X1 --hasOccupant--> Max
```

SHACL is the language that specifies constraints that allow the validation of an RDF data graph.
More specifically:
* The `subject` can be constrained by a `nodeShape`.
* The `predicate` can be constrained by a `propertyShape`

#### Rules for SHACL property shapes
For any field that resolves in scalar:
- nodeKind is sh:Literal
- name is the field name from the GraphQL schema
- path is the field name from the GraphQL schema
- datatype is the xsd literal corresponding to the scalar type

For any field that resolves in a named type:
- nodeKind is sh:IRI
- name is the named type name from the GraphQL schema
- path is the generic "model:has"
- class is the named type name from the GraphQL schema
- node is the named type shape


#### Note on supported field cases
Implicitly, lists in the default field cases GraphQL refer to an array of values that could be duplicated.
In order to explicitly say that the intended content of the array should function as a set of unique values instead, the custom directive @noDuplicates is introduced.
```gql
type Person {
    nicknamesList: [String]  # Array with possible duplicate values
    nicknamesSet: [String] @noDuplicates  # Set of unique values
}
```

The SHACL exporter does not support lists at the moment bacause adding the cardinality constraints to the list elements represent the addition of an extra blank node, and the existing use cases do not currently need that.

##### Example of a supported structure
```gql
type Cabin {
  doors: [Door] @noDuplicates
  ...
}

type Door {
  instanceTag: Area2x2
}

type Area2x2 @instanceTag {
  row: TwoRows
  column: TwoColumns
}

enum TwoRows {
  FRONT
  REAR
}

enum TwoColumns {
  DRIVERSIDE
  PASSENGERSIDE
}
```
```mermaid
graph LR
  Cabin -- has --> Door.ROW1.DRIVERSIDE
  Cabin -- has --> Door.ROW1.PASSENGERSIDE
  Cabin -- has --> Door.ROW2.DRIVERSIDE
  Cabin -- has --> Door.ROW2.PASSENGERSIDE
```
Here, each of the `object` nodes is an instance of a `Door` with a particular instance tag given as `sh:name` (e.g., `Door.ROW1.DRIVERSIDE`).
Therefore, the GraphQL non-nullable type modifier `!` can be applied only to the elements of the array and not to the array itself.
That is why not all field cases are supported at the momment by the SHACL exporter.

##### Example of an unsupported structure
```gql
type Cabin {
  doors: [Door]
  ...
}
```
```mermaid
graph LR
  Cabin -- doors --> BlankNode
  BlankNode -- has --> Door.ROW1.DRIVERSIDE
  BlankNode -- has --> Door.ROW1.PASSENGERSIDE
  BlankNode -- has --> Door.ROW2.DRIVERSIDE
  BlankNode -- has --> Door.ROW2.PASSENGERSIDE
```
This graph structure is not currently supported.
Here, there are two cardinalities: one for the list, and another for the elements in the list.

Please, refer to the CLI help for usage reference.
```bash
s2dm shacl --help
```

### JSON Schema exporter

This exporter translates the given GraphQL schema to [JSON Schema](https://json-schema.org/) format.

#### Key Features

- **Complete GraphQL Type Support**: Handles all GraphQL types including scalars, objects, enums, unions, interfaces, and lists
- **Root Type Filtering**: Use the `--root-type` flag to export only a specific type and its dependencies
- **Directive Support**: Converts S2DM directives like `@cardinality`, `@range`, and `@noDuplicates` to JSON Schema constraints
- **Reference-based Output**: Uses JSON Schema `$ref` for type references, creating clean and maintainable schemas

#### Example Transformation

Consider the following GraphQL schema:

```gql
type Vehicle {
  vin: String!
  make: String!
  model: String
  year: Int!
  engine: Engine!
  features: [String!]!
  fuelType: FuelType
}

type Engine {
  displacement: Float
  horsepower: Int
  efficiency: Float @range(min: 0.0, max: 1.0)
}

enum FuelType {
  GASOLINE
  DIESEL
  ELECTRIC
  HYBRID
}
```

The JSON Schema exporter produces:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "title": "GraphQL Schema",
  "description": "JSON Schema generated from GraphQL schema",
  "$defs": {
    "Vehicle": {
      "type": "object",
      "description": "GraphQL object type: Vehicle",
      "properties": {
        "vin": {"type": "string"},
        "make": {"type": "string"},
        "model": {"type": "string"},
        "year": {"type": "integer"},
        "engine": {"$ref": "#/$defs/Engine"},
        "features": {
          "type": "array",
          "items": {"type": "string"}
        },
        "fuelType": {"$ref": "#/$defs/FuelType"}
      }
    },
    "Engine": {
      "type": "object",
      "description": "GraphQL object type: Engine",
      "properties": {
        "displacement": {"type": "number"},
        "horsepower": {"type": "integer"},
        "efficiency": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0
        }
      }
    },
    "FuelType": {
      "type": "string",
      "enum": ["GASOLINE", "DIESEL", "ELECTRIC", "HYBRID"],
      "description": "GraphQL enum type: FuelType"
    }
  }
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
- Custom directives → `"x-directiveName": true` or `"x-directiveName": {...}`

You can call the help for usage reference:

```bash
s2dm export jsonschema --help
```

## Identifiers
With the asumption that specification files will be hosted in a certain Git repository, the tools include functions to support the proper identification of concepts and their metadata to facilite their evolution.
The identification process is based on the following principles, which are describes in the rest of this subsection:
* Concepts of interest (e.g., object types or fields) must have unique identifiers for the intended meaning. This is solved by the [creation of URIs for the concepts](#creation-of-uris-for-the-concepts).
* A concept can have multiple different realizations (i.e., incarnations) depending on the used metadata. For example, different datatypes, units, etc. This is true for the evolution of the model. However, it is assumed that the latests realization documented is the valid one. This is solved by the [creation of hashed IDs based on specified metadata](#creation-of-hashed-ids-based-on-metadata).
* A history of concepts and their realizations over time must be explicitly given as part of the model evolution. This is solved by combining concepts' URIs and their realizations into an [spec history registry](#spec-history-registry).

### Creation of URIs for the concepts
Each concept in the GraphQL schema is assigned a Uniform Resource Identifier (URI) independent of its realization.
> We refer as `realization` to the fact that a particular concept can be incarnated with some specific metadata. For instance, `Window.position` might be the concept that means the actual location in the vertical axis of the window. It might be realized with the datatype `integer`.
If the same concept would use `float` intead, only its realization (i.e., its incarnation) will change while it will conceptually remain unchanged.

The URI has the pattern:
```
{ns}:{SomeObjectName}.{someFieldname}
```
Here, `ns` is an arbitrary prefix for a particular namespace.

For instance, some URIs might be:
```
ns:Window  # URI for the Window concept
ns:Window.position  # URI for the window position
...
```
This structure is aligned with the core principle in the semantic web, in which every resource has a future-proof identifier.

The `to_concept_uri.py` script generates JSON-LD document representing the conceptual structure of the given GraphQL schema, but with the URIs.
Hence, it creates URIs for all objects, fields, and enums in the schema.




#### How It Works

1. **Schema Traversal**: The exporter traverses the GraphQL schema, identifying objects, fields, and enums.
2. **URI Generation**: For each element, a concept URI is generated using a prefix and name.
3. **JSON-LD Output**: The results are formatted as JSON-LD, with proper context and relationships between concepts.

#### Features

- Skips ID fields and the Query type
- Captures object-field relationships
- Identifies nested object relationships
- Formats output as valid JSON-LD with proper @context

#### Example

Given a GraphQL schema snippet:

```graphql
type Vehicle {
  averageSpeed(unit: Velocity_Unit_Enum = KILOMETER_PER_HOUR): Float
  adas: Vehicle_ADAS
}

type Vehicle_ADAS {
  activeAutonomyLevel: Vehicle_ADAS_ActiveAutonomyLevel_Enum
  isAutoPowerOptimize: Boolean
}

enum Vehicle_ADAS_ActiveAutonomyLevel_Enum {
  SAE_0
  SAE_5
}
```

The concept URI exporter generates:

```json
{
  "@context": {
    "ns": "https://example.org/vss#",
    "type": "@type",
    "hasField": {
      "@id": "https://example.org/vss#hasField",
      "@type": "@id"
    },
    "hasNestedObject": {
      "@id": "https://example.org/vss#hasNestedObject",
      "@type": "@id"
    },
    "Object": "https://example.org/vss#Object",
    "Enum": "https://example.org/vss#Enum",
    "Field": "https://example.org/vss#Field",
    "ObjectField": "https://example.org/vss#ObjectField"
  },
  "@graph": [
    {
      "@id": "ns:Vehicle",
      "@type": "Object",
      "hasField": ["ns:Vehicle.averageSpeed"]
    },
    {
      "@id": "ns:Vehicle_ADAS",
      "@type": "Object",
      "hasField": [
        "ns:Vehicle_ADAS.activeAutonomyLevel",
        "ns:Vehicle_ADAS.isAutoPowerOptimize"
      ]
    },
    {
      "@id": "ns:Vehicle.averageSpeed",
      "@type": "Field"
    },
    {
      "@id": "ns:Vehicle_ADAS.activeAutonomyLevel",
      "@type": "Field"
    },
    {
      "@id": "ns:Vehicle_ADAS.isAutoPowerOptimize",
      "@type": "Field"
    },
    {
      "@id": "ns:Vehicle_ADAS_ActiveAutonomyLevel_Enum",
      "@type": "Enum"
    },
    {
      "@id": "ns:Vehicle.adas",
      "@type": "ObjectField",
      "hasNestedObject": "ns:Vehicle_ADAS"
    }
  ]
}
```

This JSON-LD output shows that:
- `Vehicle` is an object type with a field
- `Vehicle.adas` has a nested object relationship with `Vehicle_ADAS` and is typed as `ObjectField`
- `Vehicle_ADAS` is an object type with two fields
- `Vehicle_ADAS_ActiveAutonomyLevel_Enum` is an enum type

### Creation of hashed IDs based on specified metadata
The ID exporter `to_id.py` traverses a GraphQL schema and generates deterministic, unique hash IDs for schema elements.
If a breaking change is introduced in the specification, it will result in a different ID.

#### How It Works

1. **Schema Traversal**: The exporter traverses the GraphQL schema, processing each type and field.
2. **Spec Generation**: For each field, an `IDGenerationSpec` is created containing:
   - Name: Fully qualified name of the field
   - Data Type: Scalar type of the field
   - Unit: Unit of measurement (if applicable)
   - Allowed Values: For enum types
   - Minimum/Maximum: Range constraints (if applicable)
3. **ID Generation**: A 32-bit FNV-1a hash is generated from these properties.

#### Example

Given a GraphQL schema like:

```graphql
type Vehicle {
  averageSpeed(unit: Velocity_Unit_Enum = KILOMETER_PER_HOUR): Float
  adas: Vehicle_ADAS
}

type Vehicle_ADAS {
  isAutoPowerOptimize: Boolean
}
```

The ID exporter generates a json output that has the element's name as the key and its ID as the value, like:

```json
{
  "Vehicle.averageSpeed": "0x9B020962",
  "Vehicle_ADAS.isAutoPowerOptimize": "0x1B10735A"
}
```

For detailed information about the ID generation mechanism, refer to the [IDGen README](../idgen/README.md).


### Spec History Registry

The `to_spec_history.py` script tracks changes in schema realizations over time. It maintains a history of realization IDs for each concept, enabling traceability of schema evolution. It can also save the complete GraphQL type definitions to history files when new or updated IDs are detected.

### How It Works

1. **Initialization**: The registry is initialized with concept URIs and their corresponding IDs.
2. **Tracking**: For each field in the schema, a `specHistory` property tracks the history of IDs with timestamps.
3. **Updates**: When schema changes occur, new IDs are appended to the history, maintaining a chronological record.
4. **Type Definition History**: The tool also saves the complete type definition for any new or updated concept to individual files in a history directory.

### Features

- Preserves the full history of realization IDs for each concept
- Records timestamps for each change
- Detects and logs new concepts and updated IDs
- Maintains valid JSON-LD structure
- Saves GraphQL type definitions to individual files for historical reference

### Example

When initialized with the concept URIs and IDs, the registry creates a JSON-LD file with specHistory:

```json
{
  "@context": {
    "ns": "https://example.org/vss#",
    "specHistory": {
      "@id": "https://example.org/vss#specHistory",
      "@container": "@list"
    },
    "hasNestedObject": {
      "@id": "https://example.org/vss#hasNestedObject",
      "@type": "@id"
    },
    "Object": "https://example.org/vss#Object",
    "Enum": "https://example.org/vss#Enum",
    "Field": "https://example.org/vss#Field",
    "ObjectField": "https://example.org/vss#ObjectField"
  },
  "@graph": [
    {
      "@id": "ns:Vehicle.averageSpeed",
      "@type": "Field",
      "specHistory": [
        {
          "id": "0x9B020962",
          "timestamp": "2025-05-14T10:22:00.000000"
        },
        {
          "id": "0xA2C48D71",
          "timestamp": "2025-05-14T10:22:30.000000"
        }
      ]
    },
    {
      "@id": "ns:Vehicle.adas",
      "@type": "ObjectField",
      "hasNestedObject": "ns:Vehicle_ADAS"
    }
  ]
}
```

This history shows that the implementation of `Vehicle.averageSpeed` changed on May 14, 2025, with new realization IDs. The registry maintains this chronological record for all concepts.

Additionally, the tool saves the complete type definition for each concept to a file in the history directory. The files are named according to the pattern `<type_name>_<YYYYMMDDHHMMSS>_<id>.graphql`, where:
- `<type_name>` is the name of the GraphQL type
- `<YYYYMMDDHHMMSS>` is the timestamp in UTC time
- `<id>` is the concept ID

For example:

```
history/
├── Vehicle_20250501111111_0x9B020962.graphql
└── Vehicle_20250502222222_0xA2C48D71.graphql
```

These files contain the complete GraphQL type definitions, allowing you to review how the type structure has changed over time. Files generated in the same batch operation will have the same timestamp.

### Usage

For initialization:
```bash
python src/tools/to_spec_history.py --concept-uri concept_uri.json --ids concept_ids.json --schema schema.graphql --output spec_history.json --init
```

For updates:
```bash
python src/tools/to_spec_history.py --concept-uri new_concept_uri.json --ids new_concept_ids.json --schema schema.graphql --spec-history spec_history.json --output updated_spec_history.json --update
```

To specify a custom history directory (default is "./history"):
```bash
python src/tools/to_spec_history.py --concept-uri concept_uri.json --ids concept_ids.json --schema schema.graphql --output spec_history.json --history-dir custom_history_dir --init
```

## TBD: Other planned functions or features
### Model validator
> TODO: Mechanisms to assess the integrity of the model. Examples: unique names, proper use of directives, completeness of types used within the model, correct construction of unique identifiers, etc.

### Arbitrary selection of concepts
> TODO: Mecahanism to arbitrarily select a sub set of the specification with only the desired concepts. Example: via the use of GraphQL introspection.
