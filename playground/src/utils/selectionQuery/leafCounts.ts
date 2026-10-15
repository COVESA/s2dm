import type { CheckedState } from "@radix-ui/react-checkbox";
import {
	type PickArgumentName,
	type PickGroup,
	resolvePickedNames,
} from "@/utils/selectionQuery/pick";
import type { SelectionIndex } from "@/utils/selectionQuery/readSelection";
import {
	getChildNodesWithinDepth,
	isLeafNode,
	type SchemaTreeNode,
} from "@/utils/selectionQuery/schemaTree";

export type LeafCounts = {
	selectedCount: number;
	totalCount: number;
};

export type PickSelection = {
	pickedNamesByArgument: Map<PickArgumentName, Set<string>>;
	counts: LeafCounts;
};

/**
 * Derives a tri-state checkbox value from a selected and a total count.
 *
 * @param selectedCount How many items are selected.
 * @param totalCount How many items can be selected.
 * @returns `true` when every item is selected, `"indeterminate"` when only
 * some are, otherwise `false`; `false` when there is nothing to select.
 */
export function getCheckedState(
	selectedCount: number,
	totalCount: number,
): CheckedState {
	if (totalCount > 0 && selectedCount === totalCount) {
		return true;
	}
	if (selectedCount > 0) {
		return "indeterminate";
	}
	return false;
}

/**
 * Resolves the picked names of every `@pick` group and counts them together
 * with the field leaves under the root.
 *
 * @param selection The index of the parsed selection query.
 * @param pickGroups The `@pick` arguments with every name they can take.
 * @param rootCounts The field leaf counts under the root.
 * @returns The picked names by argument, and the combined counts.
 */
export function countPickSelection(
	selection: SelectionIndex,
	pickGroups: PickGroup[],
	rootCounts: LeafCounts,
): PickSelection {
	const pickedNamesByArgument = new Map<PickArgumentName, Set<string>>();
	let selectedCount = rootCounts.selectedCount;
	let totalCount = rootCounts.totalCount;
	for (const { argumentName, names } of pickGroups) {
		const pickedNames = resolvePickedNames(
			selection.listedNamesByArgument,
			argumentName,
			names,
		);
		pickedNamesByArgument.set(argumentName, pickedNames);
		const pickedNameList = names.filter((name) => pickedNames.has(name));
		selectedCount += pickedNameList.length;
		totalCount += names.length;
	}

	return { pickedNamesByArgument, counts: { selectedCount, totalCount } };
}

/**
 * Creates a function that counts a node's leaves and how many of them are
 * selected, without descending into children beyond a cycle depth. A node's
 * counts are the sum of its children's, and every count is memoised by depth
 * and path key, so each node is counted once per depth and selection.
 *
 * @param selection The index of the parsed selection query.
 * @returns The counting function for that selection. It takes the node and
 * the highest recursion depth a descendant may have; by default the node's
 * own, which skips every recursive child.
 */
export function createLeafCounter(
	selection: SelectionIndex,
): (node: SchemaTreeNode, maxRecursionDepth?: number) => LeafCounts {
	const countsByKey = new Map<string, LeafCounts>();

	const countLeaves = (
		node: SchemaTreeNode,
		maxRecursionDepth = node.recursionDepth,
	): LeafCounts => {
		const cacheKey = `${maxRecursionDepth}|${node.key}`;
		const cachedCounts = countsByKey.get(cacheKey);
		if (cachedCounts) {
			return cachedCounts;
		}

		const counts: LeafCounts = { selectedCount: 0, totalCount: 0 };
		if (isLeafNode(node)) {
			counts.totalCount = 1;
			if (selection.occurrencesByKey.has(node.key)) {
				counts.selectedCount = 1;
			}
		} else {
			const childNodes = getChildNodesWithinDepth(node, maxRecursionDepth);
			for (const childNode of childNodes) {
				const childCounts = countLeaves(childNode, maxRecursionDepth);
				counts.selectedCount += childCounts.selectedCount;
				counts.totalCount += childCounts.totalCount;
			}
		}

		countsByKey.set(cacheKey, counts);
		return counts;
	};

	return countLeaves;
}
