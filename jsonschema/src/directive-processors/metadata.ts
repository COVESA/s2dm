import { DirectiveProcessor } from '../types';

export const metadataDirectiveProcessor: DirectiveProcessor = {
    directiveName: 'metadata',
    validLocations: ['FIELD_DEFINITION', 'OBJECT'],

    process(jsonSchemaNode, directiveArgs, fieldName, typeName, schema) {
        const { comment, vssType } = directiveArgs;

        if (!jsonSchemaNode['x-metadata']) {
            jsonSchemaNode['x-metadata'] = {};
        }

        if (comment) {
            jsonSchemaNode['x-metadata'].comment = comment;
        }

        if (vssType) {
            jsonSchemaNode['x-metadata'].vssType = vssType;
        }
    }
};
