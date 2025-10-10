---
title: Units CLI
weight: 20
chapter: false
---

# QUDT Units CLI

The S2DM Units CLI provides integration with the [QUDT (Quantities, Units, Dimensions and Types)](https://qudt.org/) reference model to generate standardized GraphQL unit enums. This replaces static unit definitions with a dynamic system that synchronizes directly from the authoritative QUDT repository.

## Features

- **Dynamic Unit Synchronization**: Fetch unit definitions from QUDT's GitHub repository
- **Version Management**: Support for specific QUDT versions with automatic latest version detection
- **Semantic References**: Generated enums include `@reference` directives linking to QUDT IRIs with version tags
- **UCUM Integration**: Includes UCUM codes in descriptive comments for standardization
- **SDL Validation**: Generated GraphQL enums are validated for correctness
- **Automatic Cleanup**: Removes stale files before sync to ensure fresh state

## Commands

### `s2dm units sync`

Synchronizes unit definitions from the QUDT repository and generates GraphQL enum files.

**Syntax:**
```bash
s2dm units sync --output-dir <path> [--version <version>] [--dry-run]
```

**Examples:**
```bash
# Sync latest version
s2dm units sync --output-dir units

# Sync specific version
s2dm units sync --version v3.1.5 --output-dir units

# Check what would be generated without creating files
s2dm units sync --output-dir units --dry-run

# Sync to custom directory
s2dm units sync --version v3.1.5 --output-dir path/to/qudt/units/
```

**Options:**
- `--output-dir` (required): Directory where generated unit enums will be written
- `--version` (optional): QUDT version string. Defaults to latest release if not specified
- `--dry-run` (optional): Show how many enum files would be generated without creating them

**Output:**
- Creates `<QuantityKindUnitEnum>.graphql` files (e.g., `LengthUnitEnum.graphql`)
- Generates `metadata.json` with version information
- Reports number of enum files generated

### `s2dm units check-version`

Compares the local synced QUDT version with the latest available version.

**Syntax:**
```bash
s2dm units check-version --qudt-units-dir <path>
```

**Example:**
```bash
s2dm units check-version --qudt-units-dir units/external_qudt
```

**Options:**
- `--qudt-units-dir` (required, ~/.s2dm/units/qudt by default): Directory containing generated QUDT unit enums

**Output:**
- `✓ Units are up to date.` if current version matches latest
- `⚠ There is a newer release available: X.Y.Z` if update is needed

## Generated Enum Format

Each generated enum follows this structure:

```graphql
# Generated from QUDT units catalog version 3.1.5
enum LengthUnitEnum @reference(uri: "http://qudt.org/vocab/quantitykind/Length", versionTag: "3.1.5") {
  """Meter | UCUM: m"""
  M @reference(uri: "http://qudt.org/vocab/unit/M", versionTag: "3.1.5")

  """Kilometer | UCUM: km"""
  KILOM @reference(uri: "http://qudt.org/vocab/unit/KiloM", versionTag: "3.1.5")

  """Centimeter | UCUM: cm"""
  CENTIM @reference(uri: "http://qudt.org/vocab/unit/CentiM", versionTag: "3.1.5")
  ...
}
```

**Key Elements:**
- **Enum name**: `<QuantityKind>UnitEnum` in PascalCase
- **@reference on enum**: Links to QUDT quantity kind IRI with version tag
- **@reference on values**: Links to QUDT unit IRI with version tag
- **Triple-quote docstrings**: Include human-readable label and UCUM code
- **Value names**: Use QUDT URI segments converted to SCREAMING_SNAKE_CASE

## Directory Structure

When using both QUDT and custom units, organize them as follows:

```
units/
├── external_qudt/                    # QUDT units (generated)
│   ├── metadata.json                 # Version metadata
│   ├── LengthUnitEnum.graphql        # Length units
│   ├── VelocityUnitEnum.graphql      # Velocity units
│   └── ... (500+ more unit enums)
└── custom/                           # Custom units (manual)
    ├── MyDomainUnitEnum.graphql      # Custom domain units
    └── SpecialUnitEnum.graphql       # Special use case units
```

## Workflow Example

1. **Initial Setup**: Sync units from QUDT
   ```bash
   s2dm units sync --version v3.1.5 --output-dir units/external_qudt
   ```

2. **Use Units in Schema Development**: Reference generated enums
   ```graphql
   type Vehicle {
     speed(unit: VelocityUnitEnum = KM_PER_HR): Float
     acceleration(unit: AccelerationUnitEnum = M_PER_SEC2): Float
   }
   ```

3. **Check for Updates**: Periodically check for new QUDT versions
   ```bash
   s2dm units check-version --qudt-units-dir units/external_qudt
   ```

4. **Update When Needed**: Sync newer versions as they become available
   ```bash
   s2dm units sync --version v3.2.0 --output-dir units/external_qudt
   ```

## Why URI-Based Symbols?

S2DM uses QUDT URI segments instead of labels for enum values because:

- **Consistency**: URI segments are standardized and don't vary across languages
- **Reliability**: Labels can be inconsistent, missing, or contain formatting issues
- **Semantic Accuracy**: URI segments represent the canonical QUDT identifier

## Technical Details

### Data Source
- **Repository**: [qudt/qudt-public-repo](https://github.com/qudt/qudt-public-repo)
- **File**: `src/main/rdf/vocab/unit/VOCAB_QUDT-UNITS-ALL.ttl`
- **Format**: RDF Turtle (TTL)

### Deduplication
- Uses `DISTINCT` in SPARQL queries to eliminate exact duplicates
- Filters out deprecated units to prevent symbol conflicts
- Prefers entries with UCUM codes when duplicates remain

### Error Handling
- **Network Issues**: Graceful failure with informative error messages
- **Invalid Units**: Units that cannot generate valid symbols are skipped
- **SDL Validation**: Generated GraphQL enums are validated for correctness
- **Version Check**: Safe handling of GitHub API rate limits
