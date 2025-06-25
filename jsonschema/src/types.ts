import { GraphQLSchema } from 'graphql';

export interface DirectiveProcessor {
    // The name of the directive this processor handles
    directiveName: string;

    // Locations where this directive can be applied
    validLocations: string[];

    // Function to process the directive and enhance the JSON Schema
    process(
        jsonSchemaNode: any,
        directiveArgs: Record<string, any>,
        fieldName: string,
        typeName: string,
        schema: GraphQLSchema
    ): void;
}
