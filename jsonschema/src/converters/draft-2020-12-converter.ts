/**
 * Main converter for transforming GraphQL-generated JSON Schema to Draft 2020-12 format.
 *
 * Converts JSON Schema from Draft-06 to Draft 2020-12 format with expanded inlining.
 * This function transforms GraphQL-generated JSON Schema by:
 * - Updating to Draft 2020-12 schema version
 * - Inlining all $refs to create a fully expanded schema
 * - Removing GraphQL field wrappers and artifacts
 * - Simplifying enum structures from anyOf to direct enum arrays
 * - Converting the schema to match S2DM specification format
 *
 * Assumes: GraphQL schema has exactly one Query with exactly one domain field.
 */

import { validateSchemaAssumptions } from '../validators/schema-validator';
import { extractDomainFromQuery } from '../processors/graphql-field-processor';
import { inlineAllProperties } from './property-inliner';

/**
 * Converts JSON Schema from Draft-06 to Draft 2020-12 format with expanded inlining.
 *
 * @param schema The input JSON Schema from graphql-2-json-schema (Draft-06 format)
 * @returns The transformed schema in Draft 2020-12 expanded format
 * @throws Error if the schema doesn't match expected structure
 */
export function convertToDraft202012(schema: any): any {
    // Create a deep copy
    const result = JSON.parse(JSON.stringify(schema));

    // 1. Update schema version to Draft 2020-12
    result.$schema = 'https://json-schema.org/draft/2020-12/schema';

    // 2. Validate all assumptions about schema structure
    if (!result.definitions) {
        throw new Error('No definitions found in schema. This may not be a valid GraphQL-generated JSON Schema.');
    }

    const validationResult = validateSchemaAssumptions(result);

    // Handle validation errors
    if (!validationResult.isValid) {
        console.error('Schema validation failed:');
        validationResult.errors.forEach(error => console.error(`   ${error}`));
        throw new Error('Schema does not match expected structure. See errors above.');
    }

    console.log(`Valid Query-based schema detected with domain: ${validationResult.queryFields[0]}`);

    // Extract the single domain from the Query
    const domainType = extractDomainFromQuery(result.properties.Query, result.definitions);
    if (!domainType) {
        throw new Error('Could not extract domain type from Query. Check GraphQL schema structure.');
    }

    result.type = 'object';
    result.title = domainType.name;
    result.additionalProperties = false;
    result.properties = inlineAllProperties(domainType.definition.properties || {}, result.definitions);

    if (domainType.definition.required) {
        result.required = domainType.definition.required;
    }

    // 3. Remove definitions since everything is inlined
    delete result.definitions;
    delete result.$defs;

    return result;
}
