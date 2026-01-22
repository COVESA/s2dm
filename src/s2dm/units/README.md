# QUDT Units Integration

This module provides integration with the [QUDT (Quantities, Units, Dimensions and Types)](https://qudt.org/) reference model to generate standardized GraphQL unit enums for the S2DM schema system.

## Overview

The QUDT units integration replaces static YAML-based unit definitions with a dynamic system that synchronizes unit definitions directly from the authoritative QUDT reference model. This ensures that S2DM schemas use standardized, up-to-date unit definitions with proper semantic linking.

## Features

- **Dynamic Unit Synchronization**: Fetch unit definitions from QUDT's GitHub repository
- **Version Management**: Support for specific QUDT versions with automatic latest version detection
- **English-Only Labels**: Filters for English language labels only or default (`@en`, `@en-US`)
- **Semantic References**: Generated enums include `@reference` directives linking to QUDT IRIs
- **UCUM Integration**: Includes UCUM codes in descriptive comments for standardization
- **Deduplication**: Uses DISTINCT in SPARQL query to eliminate duplicate entries and filters out deprecated units
- **SDL Validation**: Generated GraphQL enums are validated for correctness using graphql-core
- **URI-Based Symbols**: Uses QUDT URI segments as enum values for consistency and reliability (e.g., `M` instead of `METER`)

## CLI Commands

### `s2dm units sync`

Synchronizes unit definitions from the QUDT repository and generates GraphQL enum files in the `S2DM_HOME` directory (`~/.s2dm/units/qudt`).

> **Note:** Unit files are downloaded to `~/.s2dm/units/qudt` to prevent users from modifying them. This is a temporary solution. In the future, QUDT unit GraphQL files will be moved to a separate repository and referenced/downloaded from there.

```bash
# Sync latest version
s2dm units sync

# Sync specific version
s2dm units sync --version v3.1.5

# Check what would be generated without creating files
s2dm units sync --dry-run
```

**Options:**
- `--version` (optional): QUDT version string. Defaults to latest release if not specified
- `--dry-run` (optional): Shows how many enum files would be generated without actually creating any files, useful for testing and validation

**Output:**
- Creates `<QuantityKindUnitEnum>.graphql` files in `~/.s2dm/units/qudt`
- Generates `metadata.json` with version information
- Reports number of enum files generated

### `s2dm units check-version`

Compares the local synced QUDT version with the latest available version. By default, checks the `~/.s2dm/units/qudt` directory.

```bash
# Check if units are up to date
s2dm units check-version
```

**Output:**
- `✓ Units are up to date.` if current version matches latest
- `⚠ There is a newer release available: X.Y.Z` if update is needed

## Generated Output Structure

QUDT units are stored in the `S2DM_HOME` directory:

```
~/.s2dm/units/qudt/                    # QUDT units (generated, read-only)
├── metadata.json                      # Version metadata
├── LengthUnitEnum.graphql             # Length units
├── AccelerationUnitEnum.graphql       # Acceleration units
├── TemperatureUnitEnum.graphql        # Temperature units
└── ... (500+ more unit enums)
```

## Generated Enum Format

Each generated enum follows this structure:

```graphql
# Generated from QUDT units catalog version 3.1.5
enum LengthUnitEnum @reference(uri: "http://qudt.org/vocab/quantitykind/Length") {
  """Meter | UCUM: m"""
  M @reference(uri: "http://qudt.org/vocab/unit/M")

  """Kilometer | UCUM: km"""
  KILOM @reference(uri: "http://qudt.org/vocab/unit/KiloM")

  """Centimeter | UCUM: cm"""
  CENTIM @reference(uri: "http://qudt.org/vocab/unit/CentiM")

  """Millimeter | UCUM: mm"""
  MILLIM @reference(uri: "http://qudt.org/vocab/unit/MilliM")
  ...
}
```

**Key Elements:**
- **Enum name**: `<QuantityKind>UnitEnum` in PascalCase
- **@reference on enum**: Links to QUDT quantity kind IRI
- **@reference on values**: Links to QUDT unit IRI
- **Triple-quote docstrings**: Include human-readable label and UCUM code above each enum value
- **Value names**: Use QUDT URI segments converted to SCREAMING_SNAKE_CASE (e.g., `M`, `KILOM`, `CENTIM`)

**Why URI-Based Symbols?**
We use QUDT URI segments instead of labels because:
- **Consistency**: URI segments are standardized and don't vary across languages or sources
- **Reliability**: Labels in QUDT can be inconsistent, missing, or contain formatting issues
- **Brevity**: URI segments are typically shorter and more practical for code usage (e.g., `M` vs `METER`)
- **Semantic Accuracy**: URI segments represent the canonical QUDT identifier for each unit

## Integration with Registry Commands

The units system integrates with S2DM registry commands. The registry commands will automatically find and use unit enums in your schema composition:

```bash
# Generate concept IDs (automatically detects unit enums)
s2dm registry id -s schema.graphql

# Initialize registry (automatically includes unit enums)
s2dm registry init -s schema.graphql -o registry.json

# Update registry (automatically includes unit enums)
s2dm registry update -s new_schema.graphql -r registry.json
```

## Workflow Example

1. **Initial Setup**: Sync units from QUDT
   ```bash
   s2dm units sync --version v3.1.5
   ```
   This downloads unit enums to `~/.s2dm/units/qudt`.

2. **Use Units in Schema Development**: Reference generated enums in your GraphQL schemas
   ```graphql
   type Vehicle {
     speed(unit: VelocityUnitEnum = KM_PER_HR): Float
     acceleration(unit: AccelerationUnitEnum = M_PER_SEC2): Float
   }
   ```

3. **Generate Registry**: Use synced units for ID generation
   ```bash
   s2dm registry init -s vehicle.graphql -o registry.json
   ```

4. **Check for Updates**: Periodically check for new QUDT versions
   ```bash
   s2dm units check-version
   ```

5. **Update When Needed**: Sync newer versions as they become available
   ```bash
   s2dm units sync --version v3.2.0
   ```

## Technical Details

### Data Source

- **Primary**: QUDT Units Catalog from [qudt/qudt-public-repo](https://github.com/qudt/qudt-public-repo)
- **File**: `src/main/rdf/vocab/unit/VOCAB_QUDT-UNITS-ALL.ttl`
- **Format**: RDF Turtle (TTL)

### Deduplication Logic

Units are deduplicated using:
- **DISTINCT** clause in SPARQL query to eliminate exact duplicates
- **Deprecated unit filter** to prevent conflicts from deprecated/replacement pairs (e.g., `unit:Standard` vs `unit:STANDARD`)
- **Unit + Quantity Kind combination** to handle same unit across different contexts

When duplicates remain (rare edge cases), the system prefers entries that include UCUM codes.

### Symbol Generation

Enum value names are generated by:
1. **Extracting URI segment**: Take the last segment from the QUDT unit URI (after final `/`)
2. **Simple conversion**: Uppercase and replace hyphens/dots with underscores
3. **Number prefix handling**: Add `_` prefix for symbols starting with digits (e.g., `2PiRAD` → `_2PIRAD`)
4. **Validation**: Skip units that result in empty or invalid GraphQL enum symbols

This URI-based approach ensures consistent, reliable enum symbols that directly correspond to QUDT's canonical identifiers.

## Error Handling

- **Network Issues**: Graceful failure with informative error messages
- **Invalid Units**: Units that cannot generate valid enum symbols are skipped with clear logging
- **Missing URI segments**: Units with invalid URIs are filtered out during processing
- **SDL Validation**: Generated GraphQL enums are validated and errors reported if invalid
- **Version Check**: Safe handling of GitHub API rate limits with fallback to cached versions

## Dependencies

- **rdflib**: For parsing RDF/TTL files and executing SPARQL queries
- **requests**: For fetching TTL files and GitHub API calls
- **click**: For CLI interface and error handling

## Version Compatibility

- **QUDT Versions**: Supports any QUDT version with the standard repository structure
- **Backward Compatibility**: Generated enums use new naming convention (`AccelerationUnitEnum` vs `Acceleration_Unit_Enum`)
- **Schema Integration**: Works with existing S2DM schema composition system
