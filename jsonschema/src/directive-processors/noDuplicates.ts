import { DirectiveProcessor } from '../types';

export const noDuplicatesDirectiveProcessor: DirectiveProcessor = {
    directiveName: 'noDuplicates',
    validLocations: ['FIELD_DEFINITION'],

    process(jsonSchemaNode, directiveArgs, fieldName, typeName, schema) {
        // For array fields
        if (jsonSchemaNode.type === 'array') {
            jsonSchemaNode.uniqueItems = true;
        }
    }
};
