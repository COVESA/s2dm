# SKOS Mapping Structure

This document describes how GraphQL schema elements are mapped to SKOS RDF concepts and collections.

## Mapping Overview

The S2DM SKOS generation follows this hierarchical structure:

```
MyObject (GraphQL Type)
├── rdf:type → skos:Concept
├── skos:prefLabel (cardinality min:1 max:1)
├── skos:definition (optional - only if GraphQL description exists)
├── skos:note (optional - only if GraphQL description exists)
├── Must be member of ObjectConcepts collection
└── ObjectConcepts collection must have at least one member

MyObject.myField (GraphQL Field)
├── rdf:type → skos:Concept
├── skos:prefLabel (cardinality min:1 max:1)
├── skos:definition (optional - only if GraphQL description exists)
├── skos:note (optional - only if GraphQL description exists)
├── Must be member of FieldConcepts collection
└── FieldConcepts collection must have at least one member

MyEnum (GraphQL Enum)
├── rdf:type → skos:Collection
├── skos:prefLabel (cardinality min:1 max:1)
├── skos:definition (optional - only if GraphQL description exists)
├── skos:note (optional - only if GraphQL description exists)
└── MyEnumValue must be members of FieldConcepts collection

MyEnumValue (GraphQL Enum Value)
├── rdf:type → skos:Concept
├── skos:prefLabel (cardinality min:1 max:1)
├── skos:definition (optional - only if GraphQL description exists)
├── skos:note (optional - only if GraphQL description exists)
└── FieldConcepts collection must have at least one member
```

## SKOS Collections Structure

### ObjectConcepts Collection
- Contains all GraphQL object types as `skos:Concept` members
- Each object type must be a member of this collection

### FieldConcepts Collection
- Contains all GraphQL scalar/enum fields as `skos:Concept` members
- Contains all GraphQL enum values as `skos:Concept` members
- Each field and enum value must be a member of this collection

### Individual Enum Collections
- Each GraphQL enum becomes its own `skos:Collection`
- Enum values become `skos:Concept` members of their respective enum collection
- Enum values are also members of the global `FieldConcepts` collection

## SHACL Validation Rules

The generated SKOS must conform to these validation constraints:

1. **ObjectType Concepts**: Must be `skos:Concept` with required `skos:prefLabel` and collection membership
2. **Field Concepts**: Must be `skos:Concept` with required `skos:prefLabel` and collection membership
3. **EnumValue Concepts**: Must be `skos:Concept` with required `skos:prefLabel` and collection membership
4. **Collections**: Must have at least one member

## S2DM Ontology Namespace

The S2DM ontology uses the official COVESA namespace:
- **Namespace URI**: `https://covesa.global/models/s2dm#`
- **Purpose**: Provides semantic types for GraphQL schema elements in RDF/SKOS mappings
- **Types Defined**:
  - `s2dm:ObjectType` - GraphQL object types
  - `s2dm:Field` - GraphQL scalar/enum fields
  - `s2dm:EnumValue` - GraphQL enumeration values
- **Authority**: Defined by COVESA (Connected Vehicle Systems Alliance)
- **Usage**: Referenced in SHACL validation shapes and RDF generation

## Implementation Notes

- `skos:definition` and `skos:note` are **only** added when the GraphQL element has a non-empty description
- GraphQL elements without descriptions generate concepts with only `skos:prefLabel` and type information
- All concepts must have exactly one `skos:prefLabel`
- Collection membership is enforced through `skos:member` relationships
- S2DM ontology types are added alongside SKOS types for semantic precision
