import { type FieldNode, type GraphQLSchema, parse } from "graphql";
import type { InstanceTagsResponse } from "@/api/types";
import type { InstancePickTarget } from "@/utils/selectionQuery/instanceTag";
import {
	renderNames,
	renderPickDirective,
} from "@/utils/selectionQuery/patchPick";
import {
	applyEdits,
	createNodeRemoval,
	createNodeReplacement,
	createSelectionSetPrefix,
	patchSelection,
	type TextEdit,
} from "@/utils/selectionQuery/patchSelection";
import {
	findPickDirective,
	PICK_INSTANCES_ARGUMENT_NAME,
	resolveFieldPickedNames,
	toggleNames,
} from "@/utils/selectionQuery/pick";
import {
	findPickTargetFields,
	readInstancePicks,
	readPickState,
} from "@/utils/selectionQuery/readInstancePick";
import { readSelection } from "@/utils/selectionQuery/readSelection";

/**
 * Builds the edit that writes `@pick` on a field, replacing the field's
 * current `@pick` or adding one before its selection set or at its end.
 *
 * @param field The query field.
 * @param pickText The directive to write, for example
 * `@pick(instances: ["A"])`.
 * @returns The edit, or an empty list when the field has no location.
 */
function createPickWrite(field: FieldNode, pickText: string): TextEdit[] {
	const pickDirective = findPickDirective(field);
	if (pickDirective) {
		return createNodeReplacement(pickDirective, pickText);
	}

	const selectionSetPrefix = createSelectionSetPrefix(field, pickText);
	if (selectionSetPrefix.length > 0) {
		return selectionSetPrefix;
	}

	const fieldEnd = field.loc?.end;
	if (fieldEnd === undefined) {
		return [];
	}

	return [{ start: fieldEnd, end: fieldEnd, text: ` ${pickText}` }];
}

function createPickRemoval(
	selectionQuery: string,
	field: FieldNode,
): TextEdit[] {
	const pickDirective = findPickDirective(field);
	if (!pickDirective) {
		return [];
	}

	return createNodeRemoval(selectionQuery, pickDirective);
}

/**
 * Picks or unpicks instances of an instance tag field, or values of one of its
 * dimensions, by patching the selection query text. A `@pick` belongs to the
 * field's coordinate, so it is written on every place that selects the field.
 * Narrowing also selects the instance tag field with all its dimensions, which
 * the backend needs. Picking every name removes `@pick`, since a field without
 * it keeps everything. Unpicking every name changes nothing, since `@pick`
 * cannot keep no instance.
 *
 * @param selectionQuery The current selection query text; it must be valid.
 * @param schema The schema the query is validated against.
 * @param tagFields The instance tag fields, by `Type.field`.
 * @param target Where the `@pick` goes.
 * @param toggledNames The instances or values to toggle.
 * @param isChecked Whether the names are being picked or unpicked.
 * @returns The patched text, not yet formatted.
 */
export function patchInstancePick(
	selectionQuery: string,
	schema: GraphQLSchema,
	tagFields: InstanceTagsResponse,
	target: InstancePickTarget,
	toggledNames: string[],
	isChecked: boolean,
): string {
	const { tagFieldNode, pickableNames } = target;
	const document = parse(selectionQuery);
	const instancePicks = readInstancePicks(schema, tagFields, document);
	const { listedNames } = readPickState(instancePicks, target);
	const pickedNames = resolveFieldPickedNames(listedNames, pickableNames);
	const targetNames = toggleNames(
		pickableNames,
		pickedNames,
		toggledNames,
		isChecked,
	);
	if (targetNames.length === 0) {
		return selectionQuery;
	}

	const isEveryNamePicked = targetNames.length === pickableNames.length;
	if (isEveryNamePicked) {
		const pickedFields = findPickTargetFields(
			schema,
			tagFields,
			document,
			target,
		);
		const removals = pickedFields.flatMap((field) =>
			createPickRemoval(selectionQuery, field),
		);
		return applyEdits(selectionQuery, removals);
	}

	const selection = readSelection(document);
	const isSelected = true;
	const selectedQuery = patchSelection(
		selectionQuery,
		selection,
		tagFieldNode,
		isSelected,
		tagFieldNode.recursionDepth,
	);
	const selectedDocument = parse(selectedQuery);
	const pickedFields = findPickTargetFields(
		schema,
		tagFields,
		selectedDocument,
		target,
	);
	const namesText = renderNames(targetNames);
	const pickText = renderPickDirective(
		`${PICK_INSTANCES_ARGUMENT_NAME}: [${namesText}]`,
	);
	const writes = pickedFields.flatMap((field) =>
		createPickWrite(field, pickText),
	);
	return applyEdits(selectedQuery, writes);
}
