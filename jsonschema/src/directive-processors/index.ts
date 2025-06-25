import { rangeDirectiveProcessor } from './range';
import { cardinalityDirectiveProcessor } from './cardinality';
import { noDuplicatesDirectiveProcessor } from './noDuplicates';
import { instanceTagDirectiveProcessor } from './instanceTag';
import { metadataDirectiveProcessor } from './metadata';
import { DirectiveProcessor } from '../types';

// Export all processors in an array for easy registration
export const directiveProcessors: DirectiveProcessor[] = [
    rangeDirectiveProcessor,
    cardinalityDirectiveProcessor,
    noDuplicatesDirectiveProcessor,
    instanceTagDirectiveProcessor,
    metadataDirectiveProcessor,
];

// Also export them individually for direct access
export {
    rangeDirectiveProcessor,
    cardinalityDirectiveProcessor,
    noDuplicatesDirectiveProcessor,
    instanceTagDirectiveProcessor,
    metadataDirectiveProcessor,
};
