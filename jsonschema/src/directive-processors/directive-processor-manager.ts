import { GraphQLSchema, isObjectType } from 'graphql';
import { getDirectives } from '@graphql-tools/utils';
import { DirectiveProcessor } from '../types';
import { directiveProcessors } from './index';

/**
 * Processes all directives in a GraphQL schema and applies them to the JSON Schema
 * @param graphqlSchema The GraphQL schema
 * @param jsonSchema The JSON Schema to enhance with directive information
 * @returns The processed JSON Schema with directive information applied
 */
export function processDirectives(
    graphqlSchema: GraphQLSchema,
    jsonSchema: any
): any {
    // Create a map for quick lookup of processors by directive name
    const processorMap = new Map<string, DirectiveProcessor>();
    directiveProcessors.forEach(processor => {
        processorMap.set(processor.directiveName, processor);
    });

    // Process object types
    const types = graphqlSchema.getTypeMap();
    Object.values(types).forEach(type => {
        // Skip built-in types
        if (type.name.startsWith('__')) {
            return;
        }

        // Handle object types
        if (isObjectType(type)) {
            // Get directives on the type
            const typeDirectives = getDirectives(graphqlSchema, type);

            // Find the corresponding type in JSON Schema
            const jsonSchemaType = findTypeInJsonSchema(jsonSchema, type.name);

            if (jsonSchemaType) {
                // Process each directive on the type
                typeDirectives.forEach((directive: { name: string; args?: Record<string, any> }) => {
                    const processor = processorMap.get(directive.name);
                    if (processor && processor.validLocations.includes('OBJECT')) {
                        processor.process(jsonSchemaType, directive.args || {}, '', type.name, graphqlSchema);
                    }
                });
            }

            // Process fields of the object type
            const fields = type.getFields();
            Object.entries(fields).forEach(([fieldName, field]) => {
                // Get directives on the field
                const fieldDirectives = getDirectives(graphqlSchema, field);

                // Find the corresponding field in JSON Schema
                const jsonSchemaField = findFieldInJsonSchema(jsonSchema, type.name, fieldName);

                if (jsonSchemaField) {
                    // Process each directive on the field
                    fieldDirectives.forEach((directive: { name: string; args?: Record<string, any> }) => {
                        const processor = processorMap.get(directive.name);
                        if (processor && processor.validLocations.includes('FIELD_DEFINITION')) {
                            processor.process(jsonSchemaField, directive.args || {}, fieldName, type.name, graphqlSchema);
                        }
                    });
                }
            });
        }
    });

    return jsonSchema;
}

/**
 * Finds a type in the JSON Schema
 * @param jsonSchema The JSON Schema
 * @param typeName The name of the type to find
 * @returns The found type or null
 */
function findTypeInJsonSchema(jsonSchema: any, typeName: string): any {
    if (jsonSchema.definitions && jsonSchema.definitions[typeName]) {
        return jsonSchema.definitions[typeName];
    }
    return null;
}

/**
 * Finds a field in the JSON Schema (now works with cleaned/expanded format)
 * @param jsonSchema The JSON Schema
 * @param typeName The name of the type containing the field
 * @param fieldName The name of the field to find
 * @returns The found field or null
 */
function findFieldInJsonSchema(jsonSchema: any, typeName: string, fieldName: string): any {
    // For the expanded format, if we're looking for the main type, check root properties
    if (jsonSchema.title === typeName && jsonSchema.properties && jsonSchema.properties[fieldName]) {
        return jsonSchema.properties[fieldName];
    }

    // For nested types, look in the properties recursively
    return findFieldRecursively(jsonSchema.properties || {}, typeName, fieldName);
}

/**
 * Recursively searches for a field within a specific type in the expanded schema
 */
function findFieldRecursively(properties: any, typeName: string, fieldName: string): any {
    for (const [propName, propDef] of Object.entries(properties)) {
        if (typeof propDef === 'object' && propDef !== null) {
            // Check if this property represents the type we're looking for
            if ((propDef as any).properties && (propDef as any).properties[fieldName]) {
                return (propDef as any).properties[fieldName];
            }

            // Recursively search nested objects
            if ((propDef as any).properties) {
                const found = findFieldRecursively((propDef as any).properties, typeName, fieldName);
                if (found) return found;
            }
        }
    }
    return null;
}
