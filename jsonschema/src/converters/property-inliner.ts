/**
 * Property inlining utilities for JSON Schema conversion.
 *
 * Handles the expansion of $refs and creation of fully inlined schemas
 * without external references, as required by the S2DM specification.
 */

import { unwrapGraphQLField, resolveRef } from '../processors/graphql-field-processor';

/**
 * Creates an object with conditional properties based on spread operator pattern.
 *
 * @param base Base object properties
 * @param conditionals Conditional properties (undefined/null values are excluded)
 * @returns Object with base properties plus non-null/undefined conditional properties
 */
export function createObjectWithConditionals(base: Record<string, any>, conditionals: Record<string, any>): Record<string, any> {
    const result = { ...base };

    for (const [key, value] of Object.entries(conditionals)) {
        if (value !== undefined && value !== null) {
            result[key] = value;
        }
    }

    return result;
}

/**
 * Recursively inlines all properties in a schema object.
 *
 * Resolves all $refs and converts them to inline definitions,
 * removing GraphQL artifacts in the process.
 *
 * @param properties Record of property definitions to inline
 * @param definitions Available type definitions for $ref resolution
 * @returns Fully inlined properties object
 */
export function inlineAllProperties(properties: Record<string, any>, definitions: Record<string, any>): Record<string, any> {
    const result: Record<string, any> = {};

    for (const [fieldName, fieldDef] of Object.entries(properties)) {
        result[fieldName] = inlineProperty(fieldDef, definitions);
    }

    return result;
}

/**
 * Inlines a single property definition.
 *
 * Handles $ref resolution, GraphQL field wrapper removal,
 * and recursive inlining of nested objects and arrays.
 *
 * @param prop Property definition to inline
 * @param definitions Available type definitions for $ref resolution
 * @returns Fully inlined property definition
 */
export function inlineProperty(prop: any, definitions: Record<string, any>): any {
    if (!prop || typeof prop !== 'object') return prop;

    // Handle GraphQL field wrapper (return/arguments structure)
    const unwrappedProp = unwrapGraphQLField(prop);
    if (unwrappedProp !== prop) {
        return inlineProperty(unwrappedProp, definitions);
    }

    // Handle $ref resolution
    if (prop.$ref) {
        const resolvedDef = resolveRef(prop.$ref, definitions);
        if (resolvedDef) {
            return inlineProperty(resolvedDef, definitions);
        }
    }

    // Handle object types
    if (prop.type === 'object' && prop.properties) {
        return createObjectWithConditionals(
            {
                type: 'object',
                additionalProperties: false,
                properties: inlineAllProperties(prop.properties, definitions)
            },
            {
                required: prop.required,
                description: prop.description
            }
        );
    }

    // Handle array types
    if (prop.type === 'array' && prop.items) {
        return createObjectWithConditionals(
            {
                type: 'array',
                items: inlineProperty(prop.items, definitions)
            },
            {
                maxItems: prop.maxItems,
                minItems: prop.minItems
            }
        );
    }

    // Handle enum cleanup (anyOf -> enum)
    if (prop.type === 'string' && prop.anyOf && Array.isArray(prop.anyOf)) {
        const allSingleEnums = prop.anyOf.every((item: any) =>
            item.enum && Array.isArray(item.enum) && item.enum.length === 1
        );

        if (allSingleEnums) {
            const enumValues = prop.anyOf.map((item: any) => item.enum[0]);
            return createObjectWithConditionals(
                {
                    type: 'string',
                    enum: enumValues
                },
                {
                    description: prop.description
                }
            );
        }
    }

    // Handle primitives and scalars
    if (prop.type && ['string', 'number', 'integer', 'boolean'].includes(prop.type)) {
        return createObjectWithConditionals(
            {
                type: prop.type
            },
            {
                description: prop.description,
                minimum: prop.minimum,
                maximum: prop.maximum,
                pattern: prop.pattern,
                format: prop.format
            }
        );
    }

    // Return as-is for other cases
    return prop;
}
