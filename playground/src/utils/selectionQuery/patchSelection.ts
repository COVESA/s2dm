import { type ASTNode, Kind, type OperationDefinitionNode } from "graphql";
import { findPickDirective } from "@/utils/selectionQuery/pick";
import type {
	SelectionIndex,
	SelectionOccurrence,
} from "@/utils/selectionQuery/readSelection";
import {
	getNodeChain,
	getSelectableChildNodes,
	isLeafNode,
	type SchemaTreeNode,
} from "@/utils/selectionQuery/schemaTree";

export type TextEdit = {
	start: number;
	end: number;
	text: string;
};

export const NEW_OPERATION_NAME = "Selection";

/**
 * The field that keeps a query valid when `@pick` stays but no field is
 * selected, since GraphQL forbids an empty selection set.
 */
export const PLACEHOLDER_FIELD = "__typename";

export function hasOnlyPlaceholder(
	operation: OperationDefinitionNode,
): boolean {
	return operation.selectionSet.selections.every(
		(selection) =>
			selection.kind === Kind.FIELD &&
			selection.name.value === PLACEHOLDER_FIELD,
	);
}

/**
 * Builds an edit that appends a new query operation to the end of the text.
 *
 * @param selectionQuery The current selection query text.
 * @param directivesText The text between the operation name and its selection
 * set, for example ` @pick(enums: ["A"])`; empty for none.
 * @param bodyText The selections inside the operation's braces.
 * @returns The append edit.
 */
export function createOperationAppend(
	selectionQuery: string,
	directivesText: string,
	bodyText: string,
): TextEdit {
	const operationText = `query ${NEW_OPERATION_NAME}${directivesText} {\n${bodyText}\n}\n`;
	let separator = "";
	if (selectionQuery.trim()) {
		separator = "\n\n";
	}
	const end = selectionQuery.length;
	const appendedText = `${separator}${operationText}`;
	return { start: end, end, text: appendedText };
}

function getSegmentText(node: SchemaTreeNode): string {
	if (node.segment?.kind === "fragment") {
		return `... on ${node.segment.typeName}`;
	}

	return node.segment?.name ?? "";
}

/**
 * Renders a node with its whole selectable subtree.
 *
 * @param node The node to render.
 * @param maxRecursionDepth The highest recursion depth a descendant may have.
 * @returns The selection text, for example `cabin { door { isOpen } }`; for
 * the root, only the selections inside the operation's braces.
 */
function renderSubtree(
	node: SchemaTreeNode,
	maxRecursionDepth: number,
): string {
	if (isLeafNode(node)) {
		const segmentText = getSegmentText(node);
		return segmentText;
	}

	const childNodes = getSelectableChildNodes(node, maxRecursionDepth);
	const childTexts = childNodes.map((childNode) =>
		renderSubtree(childNode, maxRecursionDepth),
	);
	const body = childTexts.join("\n");
	if (!node.segment) {
		return body;
	}
	return wrapInSegment(node, body);
}

function wrapInSegment(node: SchemaTreeNode, innerText: string): string {
	const segmentText = getSegmentText(node);
	return `${segmentText} {\n${innerText}\n}`;
}

function getFirstOccurrence(
	selection: SelectionIndex,
	node: SchemaTreeNode,
): SelectionOccurrence | undefined {
	const occurrences = selection.occurrencesByKey.get(node.key);
	return occurrences?.[0];
}

const LINE_START_PATTERN = /(^|\n)[ \t]*$/;
const LINE_END_PATTERN = /^[ \t]*(\n|$)/;

/**
 * Builds an edit that inserts text on its own line just before an
 * occurrence's closing brace. No leading newline is added when the brace
 * already starts its line, so the formatter sees no blank line.
 *
 * @param selectionQuery The current selection query text.
 * @param occurrence An occurrence that owns a selection set.
 * @param text The selection text to insert.
 * @returns The edit, or `null` when the occurrence has no selection set.
 */
function createInsertion(
	selectionQuery: string,
	occurrence: SelectionOccurrence,
	text: string,
): TextEdit | null {
	const selectionSetEnd = occurrence.node.selectionSet?.loc?.end;
	if (selectionSetEnd === undefined) {
		return null;
	}

	const closingBraceOffset = selectionSetEnd - 1;
	const textBeforeBrace = selectionQuery.slice(0, closingBraceOffset);
	let insertedText = `\n${text}\n`;
	if (LINE_START_PATTERN.test(textBeforeBrace)) {
		insertedText = `${text}\n`;
	}

	return {
		start: closingBraceOffset,
		end: closingBraceOffset,
		text: insertedText,
	};
}

/**
 * Builds an edit that removes a range, widened to its whole line when nothing
 * else is on that line, so the formatter sees no leftover blank line.
 *
 * @param selectionQuery The current selection query text.
 * @param start The range start offset.
 * @param end The range end offset.
 * @returns The removal edit.
 */
function createRemoval(
	selectionQuery: string,
	start: number,
	end: number,
): TextEdit {
	const textBefore = selectionQuery.slice(0, start);
	const textAfter = selectionQuery.slice(end);
	const lineStartMatch = LINE_START_PATTERN.exec(textBefore);
	const lineEndMatch = LINE_END_PATTERN.exec(textAfter);
	if (!lineStartMatch || !lineEndMatch) {
		return { start, end, text: "" };
	}

	const leadingWhitespaceLength =
		lineStartMatch[0].length - lineStartMatch[1].length;
	return {
		start: start - leadingWhitespaceLength,
		end: end + lineEndMatch[0].length,
		text: "",
	};
}

/**
 * Builds the edit that removes an AST node's range, widened to its whole line
 * when nothing else is on that line.
 *
 * @param selectionQuery The current selection query text.
 * @param node The node to remove.
 * @returns The removal, or an empty list when the node has no location.
 */
export function createNodeRemoval(
	selectionQuery: string,
	node: ASTNode,
): TextEdit[] {
	const location = node.loc;
	if (!location) {
		return [];
	}
	const removal = createRemoval(selectionQuery, location.start, location.end);
	return [removal];
}

/**
 * Inserts every selectable descendant of a node that the text does not select
 * yet into the node's existing occurrence. The missing children of one
 * occurrence share a single insertion, so they keep schema order.
 *
 * @param selectionQuery The current selection query text.
 * @param selection The index of the current text.
 * @param node The node that already exists in the text.
 * @param occurrence The node's occurrence that receives the insertions.
 * @param maxRecursionDepth The highest recursion depth a descendant may have.
 * @returns The insertions, at most one per occurrence.
 */
function createMissingChildInsertions(
	selectionQuery: string,
	selection: SelectionIndex,
	node: SchemaTreeNode,
	occurrence: SelectionOccurrence,
	maxRecursionDepth: number,
): TextEdit[] {
	const childNodes = getSelectableChildNodes(node, maxRecursionDepth);
	const missingChildTexts: string[] = [];
	const nestedInsertions = childNodes.flatMap((childNode) => {
		const childOccurrence = getFirstOccurrence(selection, childNode);
		if (!childOccurrence) {
			const childText = renderSubtree(childNode, maxRecursionDepth);
			missingChildTexts.push(childText);
			return [];
		}

		if (isLeafNode(childNode)) {
			return [];
		}

		return createMissingChildInsertions(
			selectionQuery,
			selection,
			childNode,
			childOccurrence,
			maxRecursionDepth,
		);
	});

	if (missingChildTexts.length === 0) {
		return nestedInsertions;
	}

	const missingText = missingChildTexts.join("\n");
	const insertion = createInsertion(selectionQuery, occurrence, missingText);
	if (!insertion) {
		return nestedInsertions;
	}

	return [insertion, ...nestedInsertions];
}

/**
 * Builds the edits that select a node and its whole selectable subtree. The
 * missing part of the node's ancestor chain is inserted into the deepest
 * ancestor that already exists; a new query operation is appended when the
 * text has none. A placeholder field is removed once a real field replaces it.
 *
 * @param selectionQuery The current selection query text.
 * @param selection The index of the current text.
 * @param node The node to select.
 * @param maxRecursionDepth The highest recursion depth a descendant may have.
 * @returns The edits to apply.
 */
function createCheckEdits(
	selectionQuery: string,
	selection: SelectionIndex,
	node: SchemaTreeNode,
	maxRecursionDepth: number,
): TextEdit[] {
	const chain = getNodeChain(node);
	let anchorIndex = -1;
	let anchorOccurrence: SelectionOccurrence | undefined;
	for (const [index, chainNode] of chain.entries()) {
		const occurrence = getFirstOccurrence(selection, chainNode);
		if (!occurrence) {
			break;
		}
		anchorIndex = index;
		anchorOccurrence = occurrence;
	}

	if (anchorOccurrence && anchorIndex === chain.length - 1) {
		const childInsertions = createMissingChildInsertions(
			selectionQuery,
			selection,
			node,
			anchorOccurrence,
			maxRecursionDepth,
		);
		const placeholderRemovals = createPlaceholderRemovals(
			selectionQuery,
			selection,
			anchorOccurrence,
		);
		return [...childInsertions, ...placeholderRemovals];
	}

	let insertedText = renderSubtree(node, maxRecursionDepth);
	const missingChain = chain.slice(anchorIndex + 1, -1);
	const missingAncestors = missingChain
		.filter((ancestor) => ancestor.segment !== null)
		.reverse();
	for (const ancestor of missingAncestors) {
		insertedText = wrapInSegment(ancestor, insertedText);
	}

	if (!anchorOccurrence) {
		const operationAppend = createOperationAppend(
			selectionQuery,
			"",
			insertedText,
		);
		return [operationAppend];
	}

	const insertion = createInsertion(
		selectionQuery,
		anchorOccurrence,
		insertedText,
	);
	if (!insertion) {
		return [];
	}

	const placeholderRemovals = createPlaceholderRemovals(
		selectionQuery,
		selection,
		anchorOccurrence,
	);
	return [insertion, ...placeholderRemovals];
}

/**
 * Builds the edits that remove the placeholder field once real fields are
 * inserted into an operation that holds only the placeholder.
 *
 * @param selectionQuery The current selection query text.
 * @param selection The index of the current text.
 * @param anchorOccurrence The occurrence that receives the insertions.
 * @returns The removals; empty unless the anchor is such an operation.
 */
function createPlaceholderRemovals(
	selectionQuery: string,
	selection: SelectionIndex,
	anchorOccurrence: SelectionOccurrence,
): TextEdit[] {
	const { operation } = selection;
	if (
		!operation ||
		anchorOccurrence.node !== operation ||
		!hasOnlyPlaceholder(operation)
	) {
		return [];
	}

	return operation.selectionSet.selections.flatMap((placeholder) =>
		createNodeRemoval(selectionQuery, placeholder),
	);
}

/**
 * Builds the edit that replaces an operation's selection set with the
 * placeholder field, so an operation that keeps `@pick` stays valid.
 *
 * @param operation The operation being emptied.
 * @returns The replacement, or an empty list when the selection set has no
 * location.
 */
function createPlaceholderReplacement(
	operation: OperationDefinitionNode,
): TextEdit[] {
	const selectionSetLocation = operation.selectionSet.loc;
	if (!selectionSetLocation) {
		return [];
	}

	const placeholderReplacement: TextEdit = {
		start: selectionSetLocation.start,
		end: selectionSetLocation.end,
		text: `{\n${PLACEHOLDER_FIELD}\n}`,
	};
	return [placeholderReplacement];
}

/**
 * Marks an occurrence as removed and widens the removal to its parent when
 * that leaves the parent's selection set empty, so no `field { }` remains.
 *
 * @param occurrence The occurrence to remove.
 * @param removedNodes The AST nodes removed so far; mutated in place.
 * @returns The outermost occurrence that must be removed.
 */
function widenRemoval(
	occurrence: SelectionOccurrence,
	removedNodes: Set<ASTNode>,
): SelectionOccurrence {
	removedNodes.add(occurrence.node);
	const { parent } = occurrence;
	if (!parent) {
		return occurrence;
	}

	const siblings = parent.node.selectionSet?.selections ?? [];
	const isParentEmptied = siblings.every((sibling) =>
		removedNodes.has(sibling),
	);
	if (!isParentEmptied) {
		return occurrence;
	}

	return widenRemoval(parent, removedNodes);
}

/**
 * Builds the edits that remove every occurrence of a node, including the
 * comments inside them. Ranges nested in another removed range are dropped.
 * When this empties an operation that has `@pick`, the operation keeps a
 * placeholder field instead of being removed.
 *
 * @param selectionQuery The current selection query text.
 * @param selection The index of the current text.
 * @param node The node to deselect.
 * @returns The edits to apply.
 */
function createUncheckEdits(
	selectionQuery: string,
	selection: SelectionIndex,
	node: SchemaTreeNode,
): TextEdit[] {
	const occurrences = selection.occurrencesByKey.get(node.key) ?? [];
	const removedNodes = new Set<ASTNode>();
	const removedOccurrences = occurrences.map((occurrence) =>
		widenRemoval(occurrence, removedNodes),
	);
	const uniqueOccurrences = new Set(removedOccurrences);
	const removals = [...uniqueOccurrences].flatMap((occurrence) => {
		const { node: occurrenceNode } = occurrence;
		const isPickOperation =
			occurrenceNode.kind === Kind.OPERATION_DEFINITION &&
			findPickDirective(occurrenceNode) !== undefined;
		if (isPickOperation) {
			return createPlaceholderReplacement(occurrenceNode);
		}

		return createNodeRemoval(selectionQuery, occurrenceNode);
	});

	return removals.filter(
		(removal) =>
			!removals.some(
				(other) =>
					other !== removal &&
					other.start <= removal.start &&
					removal.end <= other.end,
			),
	);
}

/**
 * Applies text edits whose offsets all refer to the original text. Edits are
 * applied from the end of the text backwards, so earlier offsets stay valid.
 * Edits must not overlap; edits at the same offset end up in the reverse of
 * the given order, so callers merge them into one edit instead.
 *
 * @param text The original text.
 * @param edits The non-overlapping edits.
 * @returns The edited text.
 */
export function applyEdits(text: string, edits: TextEdit[]): string {
	const sortedEdits = [...edits].sort(
		(first, second) => second.start - first.start,
	);
	let editedText = text;
	for (const edit of sortedEdits) {
		editedText =
			editedText.slice(0, edit.start) + edit.text + editedText.slice(edit.end);
	}

	return editedText;
}

/**
 * Selects or deselects a tree node by patching the selection query text in
 * place. Text outside the patched ranges, including comments, field order
 * and arguments, is kept as written.
 *
 * @param selectionQuery The current selection query text.
 * @param selection The index of `selectionQuery`.
 * @param node The node to toggle.
 * @param isChecked Whether the node is being selected or deselected.
 * @param maxRecursionDepth The highest recursion depth a selected descendant
 * may have. The node's own recursion depth skips every recursive descendant.
 * @returns The patched text, not yet formatted.
 */
export function patchSelection(
	selectionQuery: string,
	selection: SelectionIndex,
	node: SchemaTreeNode,
	isChecked: boolean,
	maxRecursionDepth: number,
): string {
	let edits: TextEdit[];
	if (isChecked) {
		edits = createCheckEdits(
			selectionQuery,
			selection,
			node,
			maxRecursionDepth,
		);
	} else {
		edits = createUncheckEdits(selectionQuery, selection, node);
	}

	return applyEdits(selectionQuery, edits);
}
