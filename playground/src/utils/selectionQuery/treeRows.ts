import type { PickArgumentName, PickGroup } from "@/utils/selectionQuery/pick";
import {
	getChildNodes,
	isExpandableNode,
	type SchemaTreeNode,
} from "@/utils/selectionQuery/schemaTree";
import type { TreeSearch } from "@/utils/selectionQuery/searchTree";

type TreeRowBase = {
	key: string;
	depth: number;
	parentIndex: number | null;
};

export type FieldTreeRow = TreeRowBase & {
	kind: "field";
	node: SchemaTreeNode;
	isBeyondCycleDepth: boolean;
	isExpandable: boolean;
	isExpanded: boolean;
	isExpandedBySearch: boolean;
	highlightTerm: string;
};

export type PickGroupTreeRow = TreeRowBase & {
	kind: "pickGroup";
	argumentName: PickArgumentName;
	isExpanded: boolean;
	isExpandedBySearch: boolean;
};

export type PickNameTreeRow = TreeRowBase & {
	kind: "pickName";
	argumentName: PickArgumentName;
	name: string;
	highlightTerm: string;
};

export type TreeRow = FieldTreeRow | PickGroupTreeRow | PickNameTreeRow;

export type PickGroupRowSource = PickGroup & {
	matchingNames: Set<string> | null;
};

export function getPickGroupKey(argumentName: PickArgumentName): string {
	return `pick:${argumentName}`;
}

/**
 * Lists the `@pick` group rows and, for expanded groups, their name rows.
 *
 * @param pickGroups The `@pick` groups with their names and, under search,
 * the names that match.
 * @param expandedKeys The keys of the rows the user expanded.
 * @param highlightTerm The search term to highlight; empty when not searching.
 * @returns The rows, in display order; each knows the index of its parent row.
 */
function buildPickRows(
	pickGroups: PickGroupRowSource[],
	expandedKeys: Set<string>,
	highlightTerm: string,
): TreeRow[] {
	const rows: TreeRow[] = [];
	for (const { argumentName, names, matchingNames } of pickGroups) {
		const isSearching = matchingNames !== null;
		if (names.length === 0 || (isSearching && matchingNames.size === 0)) {
			continue;
		}

		const groupKey = getPickGroupKey(argumentName);
		const isExpanded = isSearching || expandedKeys.has(groupKey);
		const groupIndex = rows.length;
		rows.push({
			kind: "pickGroup",
			key: groupKey,
			depth: 0,
			parentIndex: null,
			argumentName,
			isExpanded,
			isExpandedBySearch: isSearching,
		});
		if (!isExpanded) {
			continue;
		}

		for (const name of names) {
			if (isSearching && !matchingNames.has(name)) {
				continue;
			}
			rows.push({
				kind: "pickName",
				key: `${groupKey}:${name}`,
				depth: 1,
				parentIndex: groupIndex,
				argumentName,
				name,
				highlightTerm,
			});
		}
	}

	return rows;
}

/**
 * Flattens the `@pick` groups and the field tree into the rows currently on
 * display, in display order. A row's children follow it when it is expanded,
 * either by the user or by the search. Under search, a search-expanded row
 * shows only the children that lead to a match; a row the user expanded shows
 * all of them.
 *
 * @param rootNode The tree's root node.
 * @param pickGroups The `@pick` groups with their names and, under search,
 * the names that match.
 * @param expandedKeys The keys of the rows the user expanded.
 * @param search The current search, or `null` when not searching.
 * @param maxRecursionDepth How many recursive fields deep a branch can be
 * expanded.
 * @returns The rows; each knows the index of its parent row.
 */
export function buildTreeRows(
	rootNode: SchemaTreeNode,
	pickGroups: PickGroupRowSource[],
	expandedKeys: Set<string>,
	search: TreeSearch | null,
	maxRecursionDepth: number,
): TreeRow[] {
	const pickHighlightTerm = search?.term ?? "";
	const rows = buildPickRows(pickGroups, expandedKeys, pickHighlightTerm);

	const appendFieldRows = (
		parentNode: SchemaTreeNode,
		depth: number,
		parentIndex: number | null,
		levelSearch: TreeSearch | null,
	) => {
		const childNodes = getChildNodes(parentNode);
		const highlightTerm = levelSearch?.term ?? "";
		for (const childNode of childNodes) {
			if (levelSearch && !levelSearch.visibleKeys.has(childNode.key)) {
				continue;
			}

			const isExpandedBySearch =
				levelSearch?.expandedKeys.has(childNode.key) ?? false;
			const isBeyondCycleDepth = childNode.recursionDepth > maxRecursionDepth;
			const isExpandable = isExpandableNode(childNode, maxRecursionDepth);
			const isExpanded =
				isExpandable && (isExpandedBySearch || expandedKeys.has(childNode.key));
			const rowIndex = rows.length;
			rows.push({
				kind: "field",
				key: childNode.key,
				depth,
				parentIndex,
				node: childNode,
				isBeyondCycleDepth,
				isExpandable,
				isExpanded,
				isExpandedBySearch,
				highlightTerm,
			});
			if (!isExpanded) {
				continue;
			}

			let childSearch: TreeSearch | null = null;
			if (isExpandedBySearch) {
				childSearch = levelSearch;
			}
			appendFieldRows(childNode, depth + 1, rowIndex, childSearch);
		}
	};
	appendFieldRows(rootNode, 0, null, search);

	return rows;
}

/**
 * Lists the indexes of a row's ancestor rows.
 *
 * @param rows The displayed rows.
 * @param rowIndex The row's index; an index past the end has no ancestors.
 * @returns The ancestor indexes, outermost first.
 */
export function getAncestorRowIndexes(
	rows: TreeRow[],
	rowIndex: number,
): number[] {
	const ancestorIndexes: number[] = [];
	let parentIndex = rows[rowIndex]?.parentIndex ?? null;
	while (parentIndex !== null) {
		ancestorIndexes.unshift(parentIndex);
		parentIndex = rows[parentIndex].parentIndex;
	}

	return ancestorIndexes;
}

/**
 * Picks the rows to pin at the top of the scrolled tree: the expanded
 * ancestors of the first row below the pinned stack. An ancestor that is
 * still on screen at or below its pinned slot is left in place, along with
 * every deeper one.
 *
 * @param rows The displayed rows.
 * @param firstVisibleIndex The index of the row at the top of the viewport.
 * @returns The indexes of the rows to pin, outermost first.
 */
export function getStickyRowIndexes(
	rows: TreeRow[],
	firstVisibleIndex: number,
): number[] {
	const firstRowAncestors = getAncestorRowIndexes(rows, firstVisibleIndex);
	// The pinned stack is about as tall as the top row's ancestor chain.
	const firstRowBelowStackIndex = firstVisibleIndex + firstRowAncestors.length;
	const ancestorIndexes = getAncestorRowIndexes(rows, firstRowBelowStackIndex);

	const stickyRowIndexes: number[] = [];
	for (const ancestorIndex of ancestorIndexes) {
		const slotsBelowTop = ancestorIndex - firstVisibleIndex;
		if (slotsBelowTop > stickyRowIndexes.length) {
			break;
		}
		stickyRowIndexes.push(ancestorIndex);
	}

	return stickyRowIndexes;
}
