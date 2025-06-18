import { DirectiveProcessor } from '../types';

export const cardinalityDirectiveProcessor: DirectiveProcessor = {
    directiveName: 'cardinality',
    validLocations: ['FIELD_DEFINITION'],

    process(jsonSchemaNode, directiveArgs, fieldName, typeName, schema) {
        const { min, max } = directiveArgs;

        // For array fields
        if (jsonSchemaNode?.properties?.return?.type === 'array') {
            if (min !== undefined) {
                jsonSchemaNode.minItems = min;
            }

            if (max !== undefined) {
                jsonSchemaNode.maxItems = max;
            }
        }
    }
};
