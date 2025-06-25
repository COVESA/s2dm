import { DirectiveProcessor } from '../types';

export const rangeDirectiveProcessor: DirectiveProcessor = {
    directiveName: 'range',
    validLocations: ['FIELD_DEFINITION'],

    process(jsonSchemaNode, directiveArgs, fieldName, typeName, schema) {
        const { min, max } = directiveArgs;

        if (min !== undefined) {
            jsonSchemaNode.minimum = min;
        }

        if (max !== undefined) {
            jsonSchemaNode.maximum = max;
        }
    }
};
