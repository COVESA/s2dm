#!/usr/bin/env node

import * as fs from 'fs';
import { graphqlSync, getIntrospectionQuery, buildSchema, IntrospectionQuery } from 'graphql';
import { fromIntrospectionQuery } from 'graphql-2-json-schema';
import { Command } from 'commander';
import { convertToDraft202012 } from './src/converters';
import { processDirectives } from './src/directive-processors/directive-processor-manager';

/**
 * Command line options for the JSON Schema generator
 */
interface CommanderOptions {
    input?: string;
    output?: string;
}

/**
 * Convert GraphQL schema to JSON Schema
 * @param {string} schemaString - GraphQL schema as string
 * @param {object} options - Conversion options
 * @returns {object} JSON Schema object
 */
function convertToJsonSchema(schemaString: string, options: { ignoreInternals: boolean, nullableArrayItems: boolean }): object {
    // Build the GraphQL schema
    const schema = buildSchema(schemaString);

    // Get the introspection query result
    const result = graphqlSync({
        schema,
        source: getIntrospectionQuery()
    });

    if (!result.data) {
        if (result.errors) {
            throw new Error(`Failed to generate introspection query: ${result.errors.map(e => e.message).join(', ')}`);
        }
        throw new Error('Failed to generate introspection query');
    }

    // Convert to JSON Schema
    // Using unknown as intermediate step for type safety
    const introspectionData = result.data as unknown;
    const jsonSchema = fromIntrospectionQuery(introspectionData as IntrospectionQuery, options);

    // Convert to Draft 2020-12 S2DM format first (clean up GraphQL wrappers)
    const convertedSchema = convertToDraft202012(jsonSchema);

    // Then process directives
    return processDirectives(schema, convertedSchema);
}

/**
 * Main function to setup and run the CLI
 */
function main(): void {
    const program = new Command();

    program
        .name('graphql2jsonschema')
        .description('Convert GraphQL schema to JSON Schema')
        .version('1.0.0');

    program
        .argument('[input-file]', 'Input GraphQL schema file')
        .option('-i, --input <file>', 'Input GraphQL schema file')
        .option('-o, --output <file>', 'Output JSON schema file (if not specified, prints to console)')
        .action((inputFileArg: string | undefined, options: CommanderOptions) => {
            try {
                // Determine input file (argument has precedence over option)
                const inputFile = inputFileArg || options.input;

                if (!inputFile) {
                    console.error('Error: Input file is required');
                    program.help();
                    return;
                }

                // Read the input file
                const schemaString = fs.readFileSync(inputFile, 'utf8');

                // Convert to JSON Schema
                const jsonSchema = convertToJsonSchema(schemaString, {
                    ignoreInternals: true,
                    nullableArrayItems: true
                });

                // Format the output
                const output = JSON.stringify(jsonSchema, null, 2);

                // Output the result
                if (options.output) {
                    fs.writeFileSync(options.output, output);
                    console.log(`JSON Schema written to ${options.output}`);
                } else {
                    console.log(output);
                }
            } catch (error: any) {
                console.error('Error:', error.message);
                if (error.stack) {
                    console.error('Stack trace:', error.stack);
                }
                process.exit(1);
            }
        });

    program.parse();
}

// Execute the main function
main();
