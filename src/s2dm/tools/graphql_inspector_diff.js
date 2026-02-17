#!/usr/bin/env node
/**
 * Node.js script to get structured JSON diff output from @graphql-inspector/core.
 *
 * This script uses the programmatic API of @graphql-inspector/core to compare
 * two GraphQL schemas and output structured JSON instead of relying on regex
 * parsing of CLI text output.
 */

const { diff } = require('@graphql-inspector/core');
const { buildSchema, printSchema } = require('graphql');
const fs = require('fs');
const path = require('path');

const oldSchemaPath = process.argv[2];
const newSchemaPath = process.argv[3];

if (!oldSchemaPath || !newSchemaPath) {
    console.error('Usage: graphql_inspector_diff.js <oldSchema> <newSchema>');
    process.exit(1);
}

(async () => {
    try {
        // Read schema files
        const oldSchemaSDL = fs.readFileSync(oldSchemaPath, 'utf8');
        const newSchemaSDL = fs.readFileSync(newSchemaPath, 'utf8');

        // Build GraphQL schema objects
        // Note: The schemas passed here are already composed and include all directives and types
        const oldSchema = buildSchema(oldSchemaSDL);
        const newSchema = buildSchema(newSchemaSDL);

        // Get diff using the programmatic API (diff() returns a Promise)
        const changes = await diff(oldSchema, newSchema);

        // Handle different return types from diff()
        let changesArray = [];
        if (Array.isArray(changes)) {
            changesArray = changes;
        } else if (changes && typeof changes === 'object') {
            // diff() might return an object with a 'changes' property
            if (changes.changes && Array.isArray(changes.changes)) {
                changesArray = changes.changes;
            } else {
                // Try to extract arrays from the object
                const allArrays = Object.values(changes).filter(Array.isArray);
                if (allArrays.length > 0) {
                    changesArray = allArrays.flat();
                } else if (Object.keys(changes).length > 0) {
                    // If it's an object with properties, it might be a change object itself
                    // or we need to check if it has a different structure
                    changesArray = [changes];
                }
            }
        }

        // Structure the output - simplified flat list (direct array)
        const result = [];

        // Process changes into simplified flat list
        for (const change of changesArray) {
            const changeType = change.type || '';
            const criticality = change.criticality || {};
            const criticalityLevel = criticality.level || 'NON_BREAKING';

            // Determine action type: insert, update, or delete
            const upperType = changeType.toUpperCase();
            let action = 'update'; // default
            if (upperType.includes('ADDED') || upperType.includes('ADD')) {
                action = 'insert';
            } else if (upperType.includes('REMOVED') || upperType.includes('REMOVE')) {
                action = 'delete';
            }

            // Extract field information
            const path = change.path || '';
            const pathParts = path.split('.');
            const typeName = pathParts.length > 0 ? pathParts[0] : null;
            const fieldName = pathParts.length > 1 ? pathParts.slice(1).join('.') : null;

            // Determine concept_name: what concept needs variant increment
            // For enum changes: use enum name (type_name)
            // For field changes: normalize to TypeName.fieldName (strip arguments/directives)
            let conceptName = path;
            const isEnumChange = upperType.includes('ENUM_VALUE');
            if (isEnumChange && typeName) {
                // Enum value change affects the enum itself
                conceptName = typeName;
            } else if (pathParts.length >= 2) {
                // For field-related changes (arguments, directives), normalize to base field
                // e.g., "Vehicle.speed.unit" -> "Vehicle.speed"
                //       "Vehicle.speed.@range.max" -> "Vehicle.speed"
                // Only take the first two parts (TypeName.fieldName)
                const baseFieldName = pathParts[1].split('@')[0]; // Remove @directive prefix if present
                conceptName = `${pathParts[0]}.${baseFieldName}`;
            }

            const structuredChange = {
                type: changeType,
                action: action,
                criticality: criticalityLevel,
                path: path,
                concept_name: conceptName,  // What concept needs variant increment
                message: change.message || '',
            };

            if (typeName) {
                structuredChange.type_name = typeName;
            }
            if (fieldName) {
                structuredChange.field_name = fieldName;
            }
            if (path) {
                structuredChange.field = path;
            }

            // Add metadata if available
            if (change.meta) {
                structuredChange.meta = change.meta;
            }

            // Add to flat changes list
            result.push(structuredChange);
        }

        // Output JSON
        console.log(JSON.stringify(result, null, 2));

        // Exit with code 1 if breaking changes detected, 0 otherwise
        const hasBreakingChanges = result.some(change =>
            change.criticality !== 'NON_BREAKING'
        );
        if (hasBreakingChanges) {
            process.exit(1);
        } else {
            process.exit(0);
        }
    } catch (error) {
        // Output error as JSON for structured error handling
        console.error(JSON.stringify({
            error: error.message,
            stack: error.stack,
            metadata: {
                old_schema: oldSchemaPath,
                new_schema: newSchemaPath,
            },
        }, null, 2));
        process.exit(2);
    }
})();
