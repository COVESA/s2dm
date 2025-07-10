# GraphQL to SKOS RDF Generation

This example demonstrates how to generate SKOS (Simple Knowledge Organization System) RDF concepts from GraphQL schemas using the S2DM SKOS exporter.

## What is SKOS?

SKOS is a W3C standard for representing knowledge organization systems (taxonomies, thesauri, classification schemes) in RDF. It provides properties like:

- `skos:prefLabel` - preferred human-readable labels
- `skos:definition` - concept definitions
- `skos:note` - additional notes
- `rdfs:seeAlso` - related resources

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

## Searching SKOS Concepts

Once you've generated a SKOS RDF file, you can search through the concepts using the built-in SPARQL-based search functionality:

```bash
s2dm search skos --ttl-file examples/graphql-to-skos/output.ttl --term Vehicle
```

### Search Command Options

- `--ttl-file/-f` - Path to TTL/RDF file containing SKOS concepts (required)
- `--term/-t` - Term to search for in SKOS concepts (required)
- `--case-insensitive/-i` - Perform case-insensitive search (default: case-sensitive)

### Search Examples

**Basic concept search:**
```bash
s2dm search skos -f output.ttl -t Vehicle
```

**Search for partial matches:**
```bash
s2dm search skos -f output.ttl -t adas
```

**Case-insensitive search:**
```bash
s2dm search skos -f output.ttl -t "vehicle" --case-insensitive
```

**Search in definitions and notes:**
```bash
s2dm search skos -f output.ttl -t "Advanced Driver"
```

### How Search Works

The search functionality uses **SPARQL queries** for efficient, scalable searches that work well with large RDF datasets. It performs **case-sensitive matching by default** and looks through:

✅ **RDF Subjects** - The full URI of each concept (e.g., finds "Vehicle" in `ns:Vehicle`)
✅ **RDF Objects** - All property values including:
- **Preferred Labels** (`skos:prefLabel`) - Human-readable names
- **Definitions** (`skos:definition`) - Concept descriptions
- **Notes** (`skos:note`) - Additional explanatory text

### Search Output

Results show matching concepts with their properties (deduplicated):

```
════════════════════ SKOS search results for 'Vehicle' ════════════════════

https://example.org/vss#Vehicle:
  definition: High-level vehicle data.
  note: Definition was inherit from the description of the element ns:Vehicle
  prefLabel: Vehicle
  seeAlso: https://example.org/vss#Vehicle
  type: http://www.w3.org/2004/02/skos/core#Concept

https://example.org/vss#Vehicle.averageSpeed:
  definition:
  note: Definition was inherit from the description of the element ns:Vehicle.averageSpeed
  prefLabel: Vehicle.averageSpeed
  seeAlso: https://example.org/vss#Vehicle.averageSpeed
  type: http://www.w3.org/2004/02/skos/core#Concept

Found 42 matching triple(s).
```

### Performance Benefits

The SPARQL-based approach provides several advantages:

1. **Scalability**: SPARQL queries are optimized by the RDF engine and scale well with large datasets
2. **Standards compliance**: Uses the W3C standard query language for RDF
3. **Future-proof**: Can easily accommodate new SKOS elements without code changes

## Input Schema

The sample GraphQL schema (`sample.graphql`) contains:

```graphql
"""High-level vehicle data."""
type Vehicle {
  id: ID!
  averageSpeed(unit: Velocity_Unit_Enum = KILOMETER_PER_HOUR): Float
  lowVoltageSystemState: Vehicle_LowVoltageSystemState_Enum
  adas: Vehicle_ADAS
}

"""All Advanced Driver Assist Systems data."""
type Vehicle_ADAS {
  isAutoPowerOptimize: Boolean
  obstacleDetection_s: [Vehicle_ADAS_ObstacleDetection]
}
```

## Expected Output

The generated RDF Turtle file will contain:

### 1. Namespace Prefixes
```turtle
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ns: <https://example.org/vss#> .
```

### 2. Type Concepts
```turtle
ns:Vehicle a skos:Concept ;
    skos:prefLabel "Vehicle"@en ;
    skos:definition "High-level vehicle data." ;
    skos:note "Definition was inherit from the description of the element ns:Vehicle" ;
    rdfs:seeAlso ns:Vehicle .

ns:Vehicle_ADAS a skos:Concept ;
    skos:prefLabel "Vehicle_ADAS"@en ;
    skos:definition "All Advanced Driver Assist Systems data." ;
    skos:note "Definition was inherit from the description of the element ns:Vehicle_ADAS" ;
    rdfs:seeAlso ns:Vehicle_ADAS .
```

### 3. Field Concepts
```turtle
ns:Vehicle.averageSpeed a skos:Concept ;
    skos:prefLabel "Vehicle.averageSpeed"@en ;
    skos:definition "" ;
    skos:note "Definition was inherit from the description of the element ns:Vehicle.averageSpeed" ;
    rdfs:seeAlso ns:Vehicle.averageSpeed .

ns:Vehicle.adas a skos:Concept ;
    skos:prefLabel "Vehicle.adas"@en ;
    skos:definition "" ;
    skos:note "Definition was inherit from the description of the element ns:Vehicle.adas" ;
    rdfs:seeAlso ns:Vehicle.adas .
```

### 4. Enum Concepts
```turtle
ns:Vehicle_LowVoltageSystemState_Enum a skos:Concept ;
    skos:prefLabel "Vehicle_LowVoltageSystemState_Enum"@en ;
    skos:definition "Vehicle LowVoltageSystemState Enum" ;
    skos:note "Definition was inherit from the description of the element ns:Vehicle_LowVoltageSystemState_Enum" ;
    rdfs:seeAlso ns:Vehicle_LowVoltageSystemState_Enum .
```

## What Gets Generated

The SKOS exporter processes:

✅ **GraphQL Object Types** → SKOS Concepts
✅ **GraphQL Fields** → SKOS Concepts (with dot notation: `Type.field`)
✅ **GraphQL Enums** → SKOS Concepts
✅ **Descriptions** → Concept definitions
✅ **BCP 47 Language Tags** → Proper internationalization

❌ **Excluded**: `Query`, `Mutation` types and `id` fields

## Validation

The generated RDF can be validated using:
- [RDF Turtle Validator](https://www.w3.org/RDF/Validator/)
- [SKOS Testing Tool](https://www.w3.org/2004/02/skos/validation)
- Standard RDF tools (Protégé, Apache Jena, etc.)
