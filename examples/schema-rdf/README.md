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

## Exclusions

- Query, Mutation, and Subscription root types
- Introspection types (`__*`)
