import {
	getChildNodes,
	getSegmentKey,
	isLeafNode,
	type SchemaTreeNode,
} from "@/utils/selectionQuery/schemaTree";

export type TreeSearch = {
	term: string;
	visibleKeys: Set<string>;
	expandedKeys: Set<string>;
};

export function normalizeSearchTerm(term: string): string {
	const trimmedTerm = term.trim();
	return trimmedTerm.toLowerCase();
}

export function matchesSearchTerm(
	text: string,
	normalizedTerm: string,
): boolean {
	const normalizedText = text.toLowerCase();
	return normalizedText.includes(normalizedTerm);
}

/**
 * Lists every node below the root that search can reach. Recursive nodes are
 * listed but not descended into, so the list is finite.
 *
 * @param rootNode The tree's root node.
 * @returns The nodes in depth-first, schema order.
 */
export function listSearchableNodes(
	rootNode: SchemaTreeNode,
): SchemaTreeNode[] {
	const nodes: SchemaTreeNode[] = [];
	const visit = (node: SchemaTreeNode) => {
		const childNodes = getChildNodes(node);
		for (const childNode of childNodes) {
			nodes.push(childNode);
			if (!childNode.isRecursive && !isLeafNode(childNode)) {
				visit(childNode);
			}
		}
	};
	visit(rootNode);

	return nodes;
}

/**
 * Finds the nodes whose label contains the search term, and the ancestors that
 * must be shown and expanded to reveal them.
 *
 * @param nodes The searchable nodes.
 * @param normalizedTerm The trimmed, lower-cased search term.
 * @returns The search, with the keys of the matches and their ancestors as
 * visible keys, and the keys of the ancestors alone as expanded keys.
 */
export function searchTree(
	nodes: SchemaTreeNode[],
	normalizedTerm: string,
): TreeSearch {
	const visibleKeys = new Set<string>();
	const expandedKeys = new Set<string>();
	for (const node of nodes) {
		if (!node.segment) {
			continue;
		}
		const label = getSegmentKey(node.segment);
		if (!matchesSearchTerm(label, normalizedTerm)) {
			continue;
		}

		visibleKeys.add(node.key);
		let ancestor = node.parent;
		while (ancestor?.segment) {
			visibleKeys.add(ancestor.key);
			expandedKeys.add(ancestor.key);
			ancestor = ancestor.parent;
		}
	}

	return { term: normalizedTerm, visibleKeys, expandedKeys };
}
