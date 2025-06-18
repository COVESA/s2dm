/**
 * Schema validation utilities for GraphQL-generated JSON Schema.
 *
 * Validates that schemas conform to expected structure:
 * - Must have a Query type with exactly one domain field
 * - Must have proper definitions structure
 */

/**
 * Result of schema validation with detailed feedback.
 */
export interface SchemaValidationResult {
    isValid: boolean;
    hasValidQuery: boolean;
    queryFieldCount: number;
    queryFields: string[];
    errors: string[];
}

/**
 * Validates all assumptions about schema structure and provides detailed feedback.
 *
 * @param schema The full JSON schema object to validate
 * @returns Validation results with details about the schema structure and any errors
 */
export function validateSchemaAssumptions(schema: any): SchemaValidationResult {
    const result: SchemaValidationResult = {
        isValid: true,
        hasValidQuery: false,
        queryFieldCount: 0,
        queryFields: [],
        errors: []
    };

    // Check if Query type exists in root properties (graphql-2-json-schema puts it there)
    if (!schema.properties || !schema.properties.Query) {
        result.isValid = false;
        result.errors.push('Expected Query type not found. Schema must have a Query type in root properties.');
        return result;
    }

    const queryDef = schema.properties.Query;

    // Check if Query has properties (through the GraphQL wrapper)
    const queryFields = getQueryFields(queryDef);
    result.queryFieldCount = queryFields.length;
    result.queryFields = queryFields;
    result.hasValidQuery = queryFields.length === 1;

    if (queryFields.length === 0) {
        result.isValid = false;
        result.errors.push('Query type has no fields. Expected exactly one domain field.');
    } else if (queryFields.length > 1) {
        result.isValid = false;
        result.errors.push(`Expected exactly one domain field in Query, found ${queryFields.length} fields.`);
        result.errors.push(`Fields found: ${queryFields.join(', ')}`);
    }

    return result;
}

/**
 * Extracts field names from a Query type definition.
 *
 * Handles GraphQL wrapper structure where fields may be nested in properties.return
 *
 * @param queryDef Query type definition
 * @returns Array of field names
 */
function getQueryFields(queryDef: any): string[] {
    // Handle GraphQL wrapper structure
    if (queryDef.properties?.return?.properties) {
        return Object.keys(queryDef.properties.return.properties);
    }
    // Direct properties
    if (queryDef.properties) {
        return Object.keys(queryDef.properties);
    }
    return [];
}
