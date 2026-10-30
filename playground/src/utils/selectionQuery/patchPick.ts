import {
	type ArgumentNode,
	type ASTNode,
	Kind,
	type ListValueNode,
	type OperationDefinitionNode,
} from "graphql";
import {
	applyEdits,
	createNodeRemoval,
	createNodeReplacement,
	createOperationAppend,
	createSelectionSetPrefix,
	hasOnlyPlaceholder,
	NEW_OPERATION_NAME,
	PLACEHOLDER_FIELD,
	type TextEdit,
} from "@/utils/selectionQuery/patchSelection";
import {
	findPickArgument,
	findPickDirective,
	getStringValues,
	PICK_DIRECTIVE_NAME,
	type PickArgumentName,
	resolvePickedNames,
	toggleNames,
} from "@/utils/selectionQuery/pick";
import type { SelectionIndex } from "@/utils/selectionQuery/readSelection";

export function renderNames(names: string[]): string {
	const quotedNames = names.map((name) => JSON.stringify(name));
	return quotedNames.join(", ");
}

export function renderPickDirective(argumentText: string): string {
	return `@${PICK_DIRECTIVE_NAME}(${argumentText})`;
}

/**
 * Tells whether an operation is written in the shorthand form `{ ... }`,
 * which has no `query` keyword, so no name or directive can be added to it
 * without the keyword.
 *
 * @param operation The query operation.
 * @returns Whether the operation starts at its selection set.
 */
function isShorthandOperation(operation: OperationDefinitionNode): boolean {
	const selectionSetStart = operation.selectionSet.loc?.start;
	return (
		selectionSetStart !== undefined &&
		operation.loc?.start === selectionSetStart
	);
}

/**
 * Builds the edits that add an argument to `@pick`, creating the directive or
 * a new query operation as needed. A new operation holds a placeholder field,
 * since GraphQL forbids an empty selection set.
 *
 * @param selectionQuery The current selection query text.
 * @param selection The index of the current text.
 * @param argumentText The argument to add, for example `enums: ["A"]`.
 * @returns The edits to apply.
 */
function createArgumentInsertion(
	selectionQuery: string,
	selection: SelectionIndex,
	argumentText: string,
): TextEdit[] {
	const directiveText = renderPickDirective(argumentText);
	const { operation } = selection;
	if (!operation) {
		const operationAppend = createOperationAppend(
			selectionQuery,
			` ${directiveText}`,
			PLACEHOLDER_FIELD,
		);
		return [operationAppend];
	}

	const pickDirective = findPickDirective(operation);
	if (!pickDirective) {
		let insertedText = directiveText;
		if (isShorthandOperation(operation)) {
			insertedText = `query ${NEW_OPERATION_NAME} ${directiveText}`;
		}
		return createSelectionSetPrefix(operation, insertedText);
	}

	const directiveEnd = pickDirective.loc?.end;
	if (directiveEnd === undefined) {
		return [];
	}
	if (!pickDirective.arguments?.length) {
		return [
			{ start: directiveEnd, end: directiveEnd, text: `(${argumentText})` },
		];
	}
	const closingParenthesisOffset = directiveEnd - 1;
	return [
		{
			start: closingParenthesisOffset,
			end: closingParenthesisOffset,
			text: `, ${argumentText}`,
		},
	];
}

/**
 * Builds the edit that removes a `@pick` argument. When it is the directive's
 * only argument, the directive is removed instead, or the whole operation when
 * only its placeholder field remains.
 *
 * @param selectionQuery The current selection query text.
 * @param operation The query operation that has the directive.
 * @param argument The argument to remove.
 * @returns The edits to apply.
 */
function createArgumentRemoval(
	selectionQuery: string,
	operation: OperationDefinitionNode,
	argument: ArgumentNode,
): TextEdit[] {
	let removedNode: ASTNode = argument;
	const pickDirective = findPickDirective(operation);
	if (pickDirective?.arguments?.length === 1) {
		removedNode = pickDirective;
		if (hasOnlyPlaceholder(operation)) {
			removedNode = operation;
		}
	}

	return createNodeRemoval(selectionQuery, removedNode);
}

/**
 * Builds the edits that add names to or remove them from a non-empty list in
 * place, so the rest of the list, including comments, is kept as written.
 *
 * @param selectionQuery The current selection query text.
 * @param list The argument's list value.
 * @param pickedNames The names the list picks now.
 * @param toggledNames The names to toggle.
 * @param isChecked Whether the names are being picked or unpicked.
 * @returns The edits to apply.
 */
function createListItemEdits(
	selectionQuery: string,
	list: ListValueNode,
	pickedNames: Set<string>,
	toggledNames: string[],
	isChecked: boolean,
): TextEdit[] {
	const listLocation = list.loc;
	if (!listLocation) {
		return [];
	}

	if (isChecked) {
		const missingNames = toggledNames.filter((name) => !pickedNames.has(name));
		const namesText = renderNames(missingNames);
		const closingBracketOffset = listLocation.end - 1;
		return [
			{
				start: closingBracketOffset,
				end: closingBracketOffset,
				text: `, ${namesText}`,
			},
		];
	}

	const stringValues = getStringValues(list);
	const removedValues = stringValues.filter((stringValue) =>
		toggledNames.includes(stringValue.value),
	);
	return removedValues.flatMap((removedValue) =>
		createNodeRemoval(selectionQuery, removedValue),
	);
}

/**
 * Picks or unpicks names in a `@pick` argument by patching the selection query
 * text in place. An empty list picks every name, so picking the last missing
 * name writes `[]`, and unpicking one name from `[]` lists the others. An
 * argument that picks nothing is removed. Text outside the patched ranges,
 * including comments, is kept as written.
 *
 * @param selectionQuery The current selection query text.
 * @param selection The index of `selectionQuery`.
 * @param argumentName The `@pick` argument.
 * @param pickableNames Every name the argument can take, in display order.
 * @param toggledNames The names to toggle.
 * @param isChecked Whether the names are being picked or unpicked.
 * @returns The patched text, not yet formatted.
 */
export function patchPick(
	selectionQuery: string,
	selection: SelectionIndex,
	argumentName: PickArgumentName,
	pickableNames: string[],
	toggledNames: string[],
	isChecked: boolean,
): string {
	const pickedNames = resolvePickedNames(
		selection.listedNamesByArgument,
		argumentName,
		pickableNames,
	);
	const targetNames = toggleNames(
		pickableNames,
		pickedNames,
		toggledNames,
		isChecked,
	);
	const { operation } = selection;
	let argument: ArgumentNode | undefined;
	if (operation) {
		argument = findPickArgument(operation, argumentName);
	}

	let edits: TextEdit[] = [];
	if (targetNames.length === 0) {
		if (operation && argument) {
			edits = createArgumentRemoval(selectionQuery, operation, argument);
		}
		return applyEdits(selectionQuery, edits);
	}

	const isEveryNamePicked = targetNames.length === pickableNames.length;
	let valueText = "[]";
	if (!isEveryNamePicked) {
		const namesText = renderNames(targetNames);
		valueText = `[${namesText}]`;
	}

	const valueLocation = argument?.value.loc;
	if (!argument || !valueLocation) {
		edits = createArgumentInsertion(
			selectionQuery,
			selection,
			`${argumentName}: ${valueText}`,
		);
	} else if (
		isEveryNamePicked ||
		argument.value.kind !== Kind.LIST ||
		argument.value.values.length === 0
	) {
		edits = createNodeReplacement(argument.value, valueText);
	} else {
		edits = createListItemEdits(
			selectionQuery,
			argument.value,
			pickedNames,
			toggledNames,
			isChecked,
		);
	}

	return applyEdits(selectionQuery, edits);
}
