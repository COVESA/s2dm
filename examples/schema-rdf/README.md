# GraphQL Schema to RDF Materialization

This example demonstrates how to materialize a GraphQL schema as RDF triples using the s2dm SKOS skeleton and ontology.

## Overview

The `schema-rdf` command transforms GraphQL SDL into RDF triples that include:

- **SKOS skeleton**: `skos:Concept`, `skos:prefLabel`, `skos:definition`
- **s2dm ontology**: Object types, fields, enum types, enum values, and type wrapper patterns

Output formats:

- **schema.nt** – Sorted n-triples (deterministic, git-friendly diffs)
- **schema.ttl** – Turtle (for consumption and release artifacts)

## Usage

```bash
s2dm generate schema-rdf \
  -s examples/schema-rdf/sample.graphql \
  -o examples/schema-rdf/output \
  --namespace "https://covesa.org/s2dm/mydomain#"
```

### Command Options

- `-s, --schema` – GraphQL schema file, directory, or URL (required, multiple)
- `-o, --output` – Output directory for schema.nt and schema.ttl (required)
- `--namespace` – Namespace URI for concept URIs (required)
- `--prefix` – Prefix for concept URIs (default: `ns`)
- `--language` – BCP 47 language tag for prefLabels (default: `en`)

### Example with Custom Options

```bash
s2dm generate schema-rdf \
  -s examples/schema-rdf/sample.graphql \
  -o ./rdf-output \
  --namespace "https://covesa.org/ontology#" \
  --prefix "veh" \
  --language "en-US"
```

## Ontology Mapping Summary

| GraphQL Element       | RDF Representation                                                                 |
|-----------------------|--------------------------------------------------------------------------------------|
| Object type           | `rdf:type skos:Concept, s2dm:ObjectType`                                            |
| Interface type        | `rdf:type skos:Concept, s2dm:InterfaceType`                                        |
| Input object type     | `rdf:type skos:Concept, s2dm:InputObjectType`                                      |
| Union type            | `rdf:type skos:Concept, s2dm:UnionType`; `s2dm:hasUnionMember`                      |
| Field                 | `rdf:type skos:Concept, s2dm:Field`; `s2dm:hasOutputType`; `s2dm:usesTypeWrapperPattern` |
| Enum type             | `rdf:type skos:Concept, s2dm:EnumType`; `s2dm:hasEnumValue`                          |
| Enum value            | `rdf:type skos:Concept, s2dm:EnumValue`                                             |
| Built-in scalar       | `s2dm:Int`, `s2dm:Float`, `s2dm:String`, `s2dm:Boolean`, `s2dm:ID`                   |
| Custom scalar/type    | `{namespace}:{TypeName}`                                                             |

### Type Wrapper Patterns

GraphQL type modifiers map to s2dm `TypeWrapperPattern`:

| GraphQL SDL      | s2dm Pattern       |
|------------------|--------------------|
| `Type`           | `bare`             |
| `Type!`          | `nonNull`         |
| `[Type]`         | `list`            |
| `[Type!]`        | `listOfNonNull`   |
| `[Type]!`        | `nonNullList`     |
| `[Type!]!`       | `nonNullListOfNonNull` |

## URI Conventions

- **Type**: `{namespace}{TypeName}` (e.g. `ns:Cabin`)
- **Field**: `{namespace}{TypeName}.{fieldName}` (e.g. `ns:Cabin.doors`)
- **Enum value**: `{namespace}{EnumName}.{ValueName}` (e.g. `ns:CabinKindEnum.SUV`)

## Example Output

For the sample schema:

```turtle
ns:Cabin a skos:Concept, s2dm:ObjectType ;
    skos:prefLabel "Cabin"@en ;
    s2dm:hasField ns:Cabin.kind, ns:Cabin.doors .

ns:Cabin.doors a skos:Concept, s2dm:Field ;
    skos:prefLabel "Cabin.doors"@en ;
    s2dm:hasOutputType ns:Door ;
    s2dm:usesTypeWrapperPattern s2dm:list .

ns:CabinKindEnum a skos:Concept, s2dm:EnumType ;
    s2dm:hasEnumValue ns:CabinKindEnum.SUV, ns:CabinKindEnum.VAN .
```

## Querying the Schema with SPARQL

The generated RDF can be queried using SPARQL -- either via the s2dm CLI or any SPARQL-capable tool (rdflib, Apache Jena, triple stores).

### Using the CLI

```bash
# Find all fields that output an enum type
s2dm query fields-outputting-enum --rdf output/schema.nt

# List all object types with their fields
s2dm query object-types-with-fields --rdf output/schema.nt

# Find fields using list wrappers (JSON output)
s2dm query list-type-fields --rdf output/schema.nt --json

# Or materialize on-the-fly from GraphQL
s2dm query fields-outputting-enum -s sample.graphql --namespace "https://example.org/my-domain#"
```

### Using rdflib (Python)

```python
from rdflib import Graph

g = Graph()
g.parse("output/schema.nt", format="nt")

results = g.query("""
    PREFIX s2dm: <https://covesa.global/models/s2dm#>
    SELECT ?field ?enumType
    WHERE {
        ?field a s2dm:Field ;
               s2dm:hasOutputType ?enumType .
        ?enumType a s2dm:EnumType .
    }
    ORDER BY ?field
""")

for row in results:
    print(f"{row.field} -> {row.enumType}")
```

### Example SPARQL Queries

**Find all fields that output an enum type:**

```sparql
PREFIX s2dm: <https://covesa.global/models/s2dm#>
SELECT ?field ?enumType WHERE {
    ?field a s2dm:Field ; s2dm:hasOutputType ?enumType .
    ?enumType a s2dm:EnumType .
}
```

**List all object types and their fields:**

```sparql
PREFIX s2dm: <https://covesa.global/models/s2dm#>
SELECT ?objectType ?field WHERE {
    ?objectType a s2dm:ObjectType ; s2dm:hasField ?field .
}
ORDER BY ?objectType
```

**Find fields using list wrappers:**

```sparql
PREFIX s2dm: <https://covesa.global/models/s2dm#>
SELECT ?field ?pattern WHERE {
    ?field a s2dm:Field ; s2dm:usesTypeWrapperPattern ?pattern .
    FILTER(?pattern IN (s2dm:list, s2dm:nonNullList, s2dm:listOfNonNull, s2dm:nonNullListOfNonNull))
}
```

**Find nested patterns (fields whose output type has enum fields):**

```sparql
PREFIX s2dm: <https://covesa.global/models/s2dm#>
SELECT ?parentType ?field ?nestedField ?enumType WHERE {
    ?parentType a s2dm:ObjectType ; s2dm:hasField ?field .
    ?field s2dm:hasOutputType ?outputType .
    ?outputType a s2dm:ObjectType ; s2dm:hasField ?nestedField .
    ?nestedField s2dm:hasOutputType ?enumType .
    ?enumType a s2dm:EnumType .
}
```

## Exclusions

- Query, Mutation, and Subscription root types
- Introspection types (`__*`)
