import { DirectiveProcessor } from '../types';

export const instanceTagDirectiveProcessor: DirectiveProcessor = {
    directiveName: 'instanceTag',
    validLocations: ['OBJECT'],

    process(jsonSchemaNode, directiveArgs, fieldName, typeName, schema) {
        // Add a custom property to mark this as an instance
        jsonSchemaNode['x-instanceTag'] = true;
    }
};
