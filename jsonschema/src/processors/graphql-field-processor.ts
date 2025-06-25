/**
 * GraphQL field processing utilities.
 *
 * Handles GraphQL-specific transformations:
 * - Unwrapping field wrappers (return/arguments structure)
 * - Resolving $refs to type definitions
 * - Extracting domain types from Query structures
 */

/**
 * Unwraps GraphQL field wrapper (return/arguments structure).
 *
 * GraphQL-to-JSON-Schema often wraps fields in a return/arguments structure.
 * This function extracts the actual field definition.
 *
 * @param fieldDef Field definition that may be wrapped
 * @returns Unwrapped field definition
 */
export function unwrapGraphQLField(fieldDef: any): any {
    return fieldDef.properties?.return ? fieldDef.properties.return : fieldDef;
}

/**
 * Resolves a $ref to its definition.
 *
 * @param ref $ref string (e.g., "#/definitions/SomeType")
 * @param definitions Available type definitions for resolution
 * @returns Resolved definition or null if not found
 */
export function resolveRef(ref: string, definitions: Record<string, any>): any | null {
    const typeName = ref.replace('#/definitions/', '');
    return definitions[typeName] || null;
}

/**
 * Extracts the single domain type from a GraphQL Query type.
 *
 * Since there's exactly one query with one domain inside,
 * this function finds that domain type by looking at the Query's properties.
 *
 * @param queryDef Query type definition
 * @param definitions All available type definitions
 * @returns Object with name and definition of the domain type, or null if not found
 */
export function extractDomainFromQuery(queryDef: any, definitions: Record<string, any>): { name: string; definition: any } | null {
    if (!queryDef.properties) return null;

    // Get the first (and only) property from the Query
    const queryFields = Object.keys(queryDef.properties);
    if (queryFields.length === 0) return null;

    // Take the first field - this should be our domain
    const fieldName = queryFields[0];
    const fieldDef = queryDef.properties[fieldName];

    // Handle GraphQL field wrapper if present
    const targetDef = unwrapGraphQLField(fieldDef);

    // If it's a $ref, resolve it to get the actual domain type
    if (targetDef.$ref) {
        const resolvedDef = resolveRef(targetDef.$ref, definitions);
        if (resolvedDef) {
            return { name: targetDef.$ref.replace('#/definitions/', ''), definition: resolvedDef };
        }
    }

    // If it's already an object definition, use it directly
    if (targetDef.type === 'object' && targetDef.properties) {
        return { name: fieldName, definition: targetDef };
    }

    return null;
}
