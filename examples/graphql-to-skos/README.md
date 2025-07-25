# GraphQL to SKOS RDF Generation

This example demonstrates how to generate SKOS (Simple Knowledge Organization System) RDF concepts from GraphQL schemas using the S2DM SKOS exporter.

## What is SKOS?

SKOS is a W3C standard for representing knowledge organization systems (taxonomies, thesauri, classification schemes) in RDF. The S2DM SKOS exporter generates core properties including:

- `skos:prefLabel` - preferred human-readable labels
- `skos:definition` - concept definitions
- `skos:note` - additional notes and provenance information

## SKOS Mapping Structure

For detailed information about how GraphQL schema elements are mapped to SKOS concepts and collections, see [SKOS Mapping Structure](skos-mapping-diagram.md). This includes the hierarchical collection structure, S2DM ontology namespace details, validation rules, and implementation details.

## Usage

Generate SKOS concepts from a GraphQL schema:

```bash
s2dm generate skos-skeleton --schema examples/graphql-to-skos/sample.graphql --output examples/graphql-to-skos/output.ttl
```

### Command Options

- `--schema` - Path to GraphQL schema file (required)
- `--output` - Output file path for RDF Turtle (.ttl recommended)
- `--namespace` - Namespace for concept URIs (default: `https://example.org/vss#`)
- `--prefix` - Prefix for concept URIs (default: `ns`)
- `--language` - BCP 47 language tag for labels (default: `en`)

### Example with Custom Options

```bash
s2dm generate skos-skeleton \
  --schema examples/graphql-to-skos/sample.graphql \
  --output examples/graphql-to-skos/output.ttl \
  --namespace "https://covesa.org/ontology#" \
  --prefix "veh" \
  --language "en-US"
```

## SHACL Validation

To validate the generated SKOS against the s2dm ontology constraints, use PySHACL:

```bash
# Generate SKOS TTL file
s2dm generate skos-skeleton --schema sample.graphql --output output.ttl

# Validate against SHACL shapes
python -m pyshacl output.ttl -s ../../test_files/shapes.shacl -f human
```

### Validation Output

- **Success**: `Conforms: True` - The SKOS is valid
- **Failure**: Detailed report showing constraint violations

### Advanced Validation Options

```bash
# Save validation report to file
python -m pyshacl output.ttl -s ../../test_files/shapes.shacl -f turtle -o validation_report.ttl

# Focus on specific shapes or nodes
python -m pyshacl output.ttl -s ../../test_files/shapes.shacl --shape https://covesa.global/models/s2dm/shapes#ObjectConceptShape
```

## Searching SKOS Concepts

Once you've generated a SKOS RDF file, you can search through the concepts using the built-in SPARQL-based search functionality:

```bash
s2dm search skos --ttl-file examples/graphql-to-skos/output.ttl --term Vehicle
```

### Search Command Options

- `--ttl-file/-f` - Path to TTL/RDF file containing SKOS concepts (required)
- `--term/-t` - Search term to look for in concept names and descriptions (required)
- `--case-insensitive/-i` - Perform case-insensitive search (optional)
- `--limit/-l` - Limit number of results (default: 10, use 'all' for unlimited)

### Search Examples

```bash
# Basic search
s2dm search skos -f output.ttl -t "Vehicle"

# Case-insensitive search with limit
s2dm search skos -f output.ttl -t "adas" -i -l 5

# Search for all matches (explicitly unlimited)
s2dm search skos -f output.ttl -t "enum" -l all
```

## Expected Output

The generated SKOS follows a hierarchical collection structure:

### Object Concepts Collection
Contains all GraphQL object types as `skos:Concept` members:
```turtle
ns:ObjectConcepts a skos:Collection ;
    skos:member ns:Vehicle, ns:Vehicle_ADAS ;
    skos:prefLabel "Object Concepts"@en .

ns:Vehicle a skos:Concept, s2dm:ObjectType ;
    skos:prefLabel "Vehicle"@en ;
    skos:definition "High-level vehicle data." ;
    skos:note "Content of SKOS definition was inherited from the description of the GraphQL SDL element Vehicle whose URI is https://example.org/vss#Vehicle." .
```

### Field Concepts Collection
Contains all GraphQL fields and enum values as `skos:Concept` members:
```turtle
ns:FieldConcepts a skos:Collection ;
    skos:member ns:Vehicle.averageSpeed, ns:Vehicle_LowVoltageSystemState_Enum.ON ;
    skos:prefLabel "Field Concepts"@en .

ns:Vehicle.averageSpeed a skos:Concept, s2dm:Field ;
    skos:prefLabel "Vehicle.averageSpeed"@en .
```

### Enum Collections
Each GraphQL enum becomes its own `skos:Collection` with enum values as members:
```turtle
ns:Vehicle_LowVoltageSystemState_Enum a skos:Collection ;
    skos:member ns:Vehicle_LowVoltageSystemState_Enum.ON, ns:Vehicle_LowVoltageSystemState_Enum.OFF ;
    skos:prefLabel "Vehicle_LowVoltageSystemState_Enum"@en ;
    skos:definition "Vehicle LowVoltageSystemState Enum" .

ns:Vehicle_LowVoltageSystemState_Enum.ON a skos:Concept, s2dm:EnumValue ;
    skos:prefLabel "Vehicle_LowVoltageSystemState_Enum.ON"@en .
```

## What Gets Generated

### Object Types
- Each GraphQL object type becomes a `skos:Concept` with `s2dm:ObjectType`
- Added to `ObjectConcepts` collection
- Uses GraphQL description as `skos:definition` if available (no fallback definitions)

### Fields (Scalar/Enum Types)
- Each scalar or enum field becomes a `skos:Concept` with `s2dm:Field`
- Added to `FieldConcepts` collection
- Uses GraphQL field description if available (no fallback definitions)

### Fields (Object References)
- Object reference fields are **excluded** (they represent relationships, not data properties)
- Only scalar and enum fields become field concepts

### Enums
- Each enum becomes a `skos:Collection`
- Each enum value becomes a `skos:Concept` with `s2dm:EnumValue`
- Enum values are members of both their enum collection and `FieldConcepts`

### Exclusions
- Query, Mutation, and Subscription types are excluded
- Object reference fields are excluded (e.g., `Vehicle.adas: ADAS` won't create `Vehicle.adas` concept)
- Built-in scalar types (String, Int, etc.) are excluded
- Fields with `@deprecated` directive are excluded
