# Registry Module

This module implements the registry for GraphQL schema elements. It includes:
- **Concept URIs**: Stable identifiers for concepts independent of realization
- **Spec History**: Tracking of concept realizations over time
- **Variant IDs**: Variant-based identifiers that increment when concepts change

## Overview
- Generate deterministic, unique IDs in the format `Concept/vM.m`
- Track concept variants over time and increment on changes (via diff)
- Maintain history of concept realizations

## Components

### Concept URI Models
- `ConceptUriNode`, `ConceptUriModel`

### Spec History Models
- `SpecHistoryEntry`, `SpecHistoryNode`, `SpecHistoryModel`

### Variant ID Models
- `VariantEntry`, `VariantIDFile`

## Variant-Based ID System

The variant ID system uses semantic versioning (vM.m) where:
- **New concepts** start at `v1.0`
- **Breaking changes** (BREAKING or DANGEROUS criticality) increment the major version (v1.0 → v2.0)
- **Non-breaking changes** (NON_BREAKING criticality) increment the minor version (v1.0 → v1.1)

### Change Types and Criticality Levels

GraphQL Inspector categorizes changes into three criticality levels:

#### BREAKING Changes (Major Version Increment)
These changes are treated as breaking and increment the major version:
- All changes with BREAKING criticality from graphql-inspector
- All changes with DANGEROUS criticality from graphql-inspector (treated as breaking)

#### NON_BREAKING Changes (Minor Version Increment)
These changes are backward compatible and increment the minor version:
- All changes with NON_BREAKING criticality from graphql-inspector

### Variant Counter

Each concept entry includes a `variant_counter` field that:
- Starts at `1` for new concepts
- Increments by 1 each time that specific concept changes
- Tracks the number of changes per concept independently

### Object Types

Object types (e.g., `Vehicle`, `Person`) are also tracked in the variant IDs file:
- Each object type gets its own entry with a variant ID (e.g., `Vehicle/v1.0`)
- Object types increment their variant when the type definition changes
- This allows tracking changes to the type structure itself, separate from field changes

IDs are saved to JSON files (typically `variant_ids_<version_tag>.json`)

## Usage
- Use `IDExporter` to generate/increment variant IDs (`Concept/vM.m`)
- Provide previous IDs and diff output to increment variants

## References
- [COVESA VSS Tools ID Documentation](https://github.com/COVESA/vss-tools/blob/master/docs/id.md)
