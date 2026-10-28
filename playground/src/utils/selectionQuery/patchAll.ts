import { Lexer, parse, Source, TokenKind } from "graphql";
import { patchPick } from "@/utils/selectionQuery/patchPick";
import { patchSelection } from "@/utils/selectionQuery/patchSelection";
import type { PickGroup } from "@/utils/selectionQuery/pick";
import {
	readSelection,
	type SelectionIndex,
} from "@/utils/selectionQuery/readSelection";
import type { SchemaTreeNode } from "@/utils/selectionQuery/schemaTree";

function isCommentOnly(selectionQuery: string): boolean {
	const source = new Source(selectionQuery);
	const lexer = new Lexer(source);
	const firstToken = lexer.advance();
	return firstToken.kind === TokenKind.EOF;
}

function indexText(selectionQuery: string): SelectionIndex {
	if (isCommentOnly(selectionQuery)) {
		return readSelection(null);
	}

	const document = parse(selectionQuery);
	return readSelection(document);
}

/**
 * Selects or deselects everything selectable: every field under the root
 * within the cycle depth, and every name of each `@pick` argument. The field patch and each `@pick` patch
 * are applied in turn, re-reading the text between them because every patch
 * moves the AST locations the next one relies on.
 *
 * @param selectionQuery The current selection query text.
 * @param rootNode The tree's root node.
 * @param pickGroups The `@pick` arguments with every name they can take.
 * @param isChecked Whether everything is being selected or deselected.
 * @param maxRecursionDepth How many recursive fields deep a selected path may
 * go.
 * @returns The patched text, not yet formatted.
 */
export function patchAll(
	selectionQuery: string,
	rootNode: SchemaTreeNode,
	pickGroups: PickGroup[],
	isChecked: boolean,
	maxRecursionDepth: number,
): string {
	const fieldSelection = indexText(selectionQuery);
	let patchedQuery = patchSelection(
		selectionQuery,
		fieldSelection,
		rootNode,
		isChecked,
		maxRecursionDepth,
	);

	for (const { argumentName, names } of pickGroups) {
		if (names.length === 0) {
			continue;
		}
		const pickSelection = indexText(patchedQuery);
		patchedQuery = patchPick(
			patchedQuery,
			pickSelection,
			argumentName,
			names,
			names,
			isChecked,
		);
	}

	return patchedQuery;
}
