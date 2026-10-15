import {
	type DocumentNode,
	type FieldNode,
	type InlineFragmentNode,
	Kind,
	type OperationDefinitionNode,
	type SelectionSetNode,
} from "graphql";
import { readListedNames } from "@/utils/selectionQuery/pick";
import { joinPathKey } from "@/utils/selectionQuery/schemaTree";

export type SelectionOccurrence = {
	node: OperationDefinitionNode | FieldNode | InlineFragmentNode;
	parent: SelectionOccurrence | null;
};

export type SelectionIndex = {
	operation: OperationDefinitionNode | null;
	occurrencesByKey: Map<string, SelectionOccurrence[]>;
	listedNamesByArgument: Map<string, Set<string>>;
};

export function createEmptySelectionIndex(): SelectionIndex {
	return {
		operation: null,
		occurrencesByKey: new Map(),
		listedNamesByArgument: new Map(),
	};
}

function addOccurrence(
	occurrencesByKey: Map<string, SelectionOccurrence[]>,
	key: string,
	occurrence: SelectionOccurrence,
): void {
	const occurrences = occurrencesByKey.get(key) ?? [];
	occurrences.push(occurrence);
	occurrencesByKey.set(key, occurrences);
}

/**
 * Records every field and typed inline fragment of a selection set under its
 * path key. Inline fragments without a type condition are transparent: their
 * selections keep the parent's path key.
 *
 * @param selectionSet The selection set to walk.
 * @param parentKey The path key of the selection set's owner.
 * @param parent The occurrence that owns the selection set.
 * @param occurrencesByKey The index being filled; mutated in place.
 */
function indexSelectionSet(
	selectionSet: SelectionSetNode,
	parentKey: string,
	parent: SelectionOccurrence,
	occurrencesByKey: Map<string, SelectionOccurrence[]>,
): void {
	for (const selection of selectionSet.selections) {
		if (selection.kind === Kind.FRAGMENT_SPREAD) {
			continue;
		}

		const occurrence: SelectionOccurrence = { node: selection, parent };
		let key = parentKey;
		if (selection.kind === Kind.FIELD) {
			key = joinPathKey(parentKey, {
				kind: "field",
				name: selection.name.value,
			});
			addOccurrence(occurrencesByKey, key, occurrence);
		} else if (selection.typeCondition) {
			key = joinPathKey(parentKey, {
				kind: "fragment",
				typeName: selection.typeCondition.name.value,
			});
			addOccurrence(occurrencesByKey, key, occurrence);
		}

		if (selection.selectionSet) {
			indexSelectionSet(
				selection.selectionSet,
				key,
				occurrence,
				occurrencesByKey,
			);
		}
	}
}

/**
 * Indexes the first query operation of a validated selection query by path
 * key, and reads the names listed in its `@pick` directive. The operation
 * itself is stored under the empty root key.
 *
 * @param document The parsed, validated selection query; `null` for empty
 * text.
 * @returns The index, empty when there is no query operation.
 */
export function readSelection(document: DocumentNode | null): SelectionIndex {
	if (!document) {
		return createEmptySelectionIndex();
	}

	const operation = document.definitions.find(
		(definition): definition is OperationDefinitionNode =>
			definition.kind === Kind.OPERATION_DEFINITION &&
			definition.operation === "query",
	);
	if (!operation) {
		return createEmptySelectionIndex();
	}

	const occurrencesByKey = new Map<string, SelectionOccurrence[]>();
	const rootOccurrence: SelectionOccurrence = { node: operation, parent: null };
	addOccurrence(occurrencesByKey, "", rootOccurrence);
	indexSelectionSet(
		operation.selectionSet,
		"",
		rootOccurrence,
		occurrencesByKey,
	);
	const listedNamesByArgument = readListedNames(operation);

	return { operation, occurrencesByKey, listedNamesByArgument };
}
