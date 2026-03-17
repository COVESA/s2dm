#!/bin/bash
# Example workflow demonstrating spec history registry generation
# This script shows the complete workflow from initial schema to updated schema with variant tracking

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use uv run s2dm when running from project root (has pyproject.toml and uv available)
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
if command -v uv &>/dev/null && [ -f "${PROJECT_ROOT}/pyproject.toml" ]; then
  S2DM_CMD="uv run s2dm"
else
  S2DM_CMD="s2dm"
fi

# Configuration - all paths relative to script directory
SCHEMA_DIR="${SCRIPT_DIR}"
OUTPUT_DIR="${SCRIPT_DIR}/output"
SCHEMA_FILE="${SCHEMA_DIR}/sample.graphql"
SCHEMA_UPDATED_FILE="${SCHEMA_DIR}/sample_updated.graphql"
# Sample schemas are self-contained (no external units). External QUDT units use @reference
# and require schema processing; use only the sample files for this workflow.
NAMESPACE="https://example.org/vss#"
PREFIX="ns"
VERSION_TAG_INIT="v1.0.0"
VERSION_TAG_UPDATED="v1.1.0"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

echo "=========================================="
echo "Step 1: Generate initial variant IDs"
echo "=========================================="
${S2DM_CMD} registry id \
  --schema "${SCHEMA_FILE}" \
  --output "${OUTPUT_DIR}/variant_ids.json" \
  --version-tag "${VERSION_TAG_INIT}"

echo ""
echo "=========================================="
echo "Step 2: Generate concept URIs"
echo "=========================================="
${S2DM_CMD} registry concept-uri \
  --schema "${SCHEMA_FILE}" \
  --output "${OUTPUT_DIR}/concept_uri.json" \
  --namespace "${NAMESPACE}" \
  --prefix "${PREFIX}"

echo ""
echo "=========================================="
echo "Step 3: Initialize spec history registry"
echo "=========================================="
${S2DM_CMD} registry init \
  --schema "${SCHEMA_FILE}" \
  --output "${OUTPUT_DIR}/spec_history_${VERSION_TAG_INIT}.json" \
  --concept-namespace "${NAMESPACE}" \
  --concept-prefix "${PREFIX}" \
  --version-tag "${VERSION_TAG_INIT}"

echo ""
echo "=========================================="
echo "Step 4: Generate diff between schemas"
echo "=========================================="
${S2DM_CMD} diff graphql \
  --schema "${SCHEMA_FILE}" \
  --val-schema "${SCHEMA_UPDATED_FILE}" \
  --output "${OUTPUT_DIR}/diff.json" || true  # Continue even if diff has breaking changes

echo ""
echo "=========================================="
echo "Step 5: Generate updated variant IDs using diff"
echo "=========================================="
${S2DM_CMD} registry id \
  --schema "${SCHEMA_UPDATED_FILE}" \
  --output "${OUTPUT_DIR}/variant_ids.json" \
  --previous-ids "${OUTPUT_DIR}/variant_ids_${VERSION_TAG_INIT}.json" \
  --diff-file "${OUTPUT_DIR}/diff.json" \
  --version-tag "${VERSION_TAG_UPDATED}"

echo ""
echo "=========================================="
echo "Step 6: Generate updated concept URIs"
echo "=========================================="
${S2DM_CMD} registry concept-uri \
  --schema "${SCHEMA_UPDATED_FILE}" \
  --output "${OUTPUT_DIR}/concept_uri_updated.json" \
  --namespace "${NAMESPACE}" \
  --prefix "${PREFIX}"

echo ""
echo "=========================================="
echo "Step 7: Update spec history registry"
echo "=========================================="
${S2DM_CMD} registry update \
  --schema "${SCHEMA_UPDATED_FILE}" \
  --spec-history "${OUTPUT_DIR}/spec_history_${VERSION_TAG_INIT}.json" \
  --output "${OUTPUT_DIR}/spec_history.json" \
  --previous-ids "${OUTPUT_DIR}/variant_ids_${VERSION_TAG_INIT}.json" \
  --diff-file "${OUTPUT_DIR}/diff.json" \
  --concept-namespace "${NAMESPACE}" \
  --concept-prefix "${PREFIX}" \
  --version-tag "${VERSION_TAG_UPDATED}"

echo ""
echo "=========================================="
echo "Workflow complete!"
echo "=========================================="
echo ""
echo "Generated files:"
echo "  - ${OUTPUT_DIR}/variant_ids_${VERSION_TAG_INIT}.json (initial variant IDs)"
echo "  - ${OUTPUT_DIR}/variant_ids_${VERSION_TAG_UPDATED}.json (updated variant IDs with semantic version increments)"
echo "  - ${OUTPUT_DIR}/concept_uri.json (initial URIs)"
echo "  - ${OUTPUT_DIR}/concept_uri_updated.json (updated URIs)"
echo "  - ${OUTPUT_DIR}/spec_history_${VERSION_TAG_INIT}.json (initial spec history)"
echo "  - ${OUTPUT_DIR}/spec_history_${VERSION_TAG_UPDATED}.json (updated spec history)"
echo "  - ${OUTPUT_DIR}/diff.json (schema diff)"
echo "  - ${OUTPUT_DIR}/history/ (type definition history files)"
echo ""
echo "You can inspect the files to see:"
echo "  - How variant IDs use semantic versioning (v1.0, v1.1, v2.0) based on change criticality"
echo "  - How variant_counter increments per concept when changes occur"
echo "  - How object types are tracked alongside fields and enums"
echo "  - How spec history entries include both variant ID and version_tag"
echo "  - How the diff identifies breaking (major version) and non-breaking (minor version) changes"
echo "  - Individual GraphQL type definitions saved in the history folder"
