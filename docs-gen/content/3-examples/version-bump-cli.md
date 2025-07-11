---
title: Version Bump CLI Examples
weight: 60
---

This section contains examples demonstrating different scenarios for the `s2dm check version-bump` command, based on GraphQL Inspector's change detection.

## Overview

The version-bump command analyzes GraphQL schema changes and recommends the appropriate semantic version bump:

- **No version bump**: Identical schemas
- **Patch/Minor bump**: Non-breaking changes (new optional fields, enum values)
- **Major bump**: Breaking changes (removed fields, type changes)
- **Dangerous changes**: Potentially problematic but not immediately breaking

## Examples

### 1. No Version Bump Needed

**Command:**

```bash
s2dm check version-bump -s no-change.graphql -p base.graphql
```

**Expected Output:**

```bash
No version bump needed
```

**Scenario:** Both schemas are identical, no changes detected.

### 2. Non-Breaking Change (Minor/Patch Bump)

**Command:**

```bash
s2dm check version-bump -s non-breaking.graphql -p base.graphql
```

**Expected Output:**

```bash
Patch version bump needed
```

**Changes:**

- Added new optional fields: `Vehicle.owner`, `Vehicle.mileage`, `Engine.fuelEfficiency`

These changes are backwards compatible and won't break existing clients.

### 3. Dangerous Change

**Command:**

```bash
s2dm check version-bump -s dangerous.graphql -p base.graphql
```

**Expected Output:**

```bash
Minor version bump needed
```

**Changes:**

- Added new enum value: `EngineType.HYDROGEN`

Note: GraphQL Inspector may classify these as dangerous changes depending on configuration, but they're typically backwards compatible due to default values.

### 4. Breaking Change (Major Bump)

**Command:**

```bash
s2dm check version-bump -s breaking.graphql -p base.graphql
```

**Expected Output:**

```bash
Detected breaking changes, major version bump needed. Please run diff to get more details
```

**Changes:**

- Removed field: `Vehicle.color`
- Changed field type: `Vehicle.owner` from `String` to `Int`
- Changed field type: `Engine.displacement` from `Float` to `Int`
- Removed enum value: `EngineType.HYBRID`

These changes will break existing clients that depend on the removed/changed fields.

## Understanding Change Types

### Non-Breaking Changes ✅

- Adding new optional fields
- Adding new enum values
- Adding new types
- Adding new queries/mutations
- Adding descriptions/deprecation notices

### Dangerous Changes ⚠️

- Adding arguments to existing fields (with defaults)
- Changing field descriptions significantly
- Adding interfaces to existing types

### Breaking Changes ❌

- Removing fields, types, or enum values
- Changing field types incompatibly
- Making optional fields required
- Removing or changing arguments
- Changing field nullability (nullable to non-nullable)

## Running the Examples

To test these examples:

```bash
# Navigate to the test data directory
cd tests/data

# Test each scenario
s2dm check version-bump -s no-change.graphql -p base.graphql
s2dm check version-bump -s non-breaking.graphql -p base.graphql
s2dm check version-bump -s dangerous.graphql -p base.graphql
s2dm check version-bump -s breaking.graphql -p base.graphql
```

## Additional Commands

For more detailed analysis, use the diff command:

```bash
s2dm diff graphql -s breaking.graphql -v base.graphql
```

This will provide a comprehensive breakdown of all changes detected between the schemas.

## Pipeline Usage

For pipeline automation, use the `--output-type` flag to get machine-readable output:

```bash
# Returns: none, patch, minor, or major
VERSION_BUMP=$(s2dm check version-bump -s new-schema.graphql -p old-schema.graphql --output-type)

# Example pipeline usage:
if [[ "$VERSION_BUMP" == "major" ]]; then
    echo "Breaking changes detected, requires manual review"
    exit 1
elif [[ "$VERSION_BUMP" == "minor" ]]; then
    echo "Minor version bump needed"
    # bump-my-version bump minor
elif [[ "$VERSION_BUMP" == "patch" ]]; then
    echo "Patch version bump needed"
    # bump-my-version bump patch
else
    echo "No version bump needed"
fi
```

## Return Values

- **none**: No changes detected
- **patch**: Non-breaking changes only (✔ symbols in diff)
- **minor**: Dangerous changes detected (⚠ symbols in diff)
- **major**: Breaking changes detected (✖ symbols in diff)
