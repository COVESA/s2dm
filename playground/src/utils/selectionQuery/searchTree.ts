import { splitElementId, toElementId } from "@search-ui/utils/elementId";
import { matchesSearchTerm } from "@search-ui/utils/textSearch";
import { type GraphQLSchema, isEnumType } from "graphql";
import {
	getChildNodes,
	getSegmentKey,
	isLeafNode,
	type SchemaTreeNode,
	type SchemaTreeSegment,
} from "@/utils/selectionQuery/schemaTree";

export type TreeSearch = {
	/** The typed text to highlight inside labels; empty for none. */
	term: string;
	visibleKeys: Set<string>;
	expandedKeys: Set<string>;
	/** The keys of the nodes that matched, without the ancestors shown to reveal them. */
	matchedKeys: Set<string>;
	/** Whether matched labels are highlighted whole instead of at `term`. */
	highlightsWholeMatch: boolean;
};

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
 * Collects the matching nodes and the ancestors that must be shown and expanded
 * to reveal them.
 *
 * @param nodes The searchable nodes.
 * @param isMatch Whether a node, with its segment, matches the search.
 * @param highlightTerm The typed text to highlight in labels; empty for none.
 * @param highlightsWholeMatch Whether matched labels are highlighted whole.
 * @returns The search, with the keys of the matches as matched keys, the keys
 * of the matches and their ancestors as visible keys, and the keys of the
 * ancestors alone as expanded keys.
 */
function revealMatchingNodes(
	nodes: SchemaTreeNode[],
	isMatch: (node: SchemaTreeNode, segment: SchemaTreeSegment) => boolean,
	highlightTerm: string,
	highlightsWholeMatch: boolean,
): TreeSearch {
	const visibleKeys = new Set<string>();
	const expandedKeys = new Set<string>();
	const matchedKeys = new Set<string>();
	for (const node of nodes) {
		if (!node.segment || !isMatch(node, node.segment)) {
			continue;
		}

		matchedKeys.add(node.key);
		visibleKeys.add(node.key);
		let ancestor = node.parent;
		while (ancestor?.segment) {
			visibleKeys.add(ancestor.key);
			expandedKeys.add(ancestor.key);
			ancestor = ancestor.parent;
		}
	}

	return {
		term: highlightTerm,
		visibleKeys,
		expandedKeys,
		matchedKeys,
		highlightsWholeMatch,
	};
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
	return revealMatchingNodes(
		nodes,
		(_node, segment) => {
			const label = getSegmentKey(segment);
			return matchesSearchTerm(label, normalizedTerm);
		},
		normalizedTerm,
		false,
	);
}

export type ElementMatches = {
	/** `Type.field` ids of matched fields. */
	fieldIds: Set<string>;
	/** Names of matched object, interface, and enum types. */
	typeNames: Set<string>;
};

/**
 * Sorts semantic search result ids into matched fields and matched types.
 * Enum values have no tree nodes, so a matched `Enum.VALUE` matches its enum.
 *
 * For example, `["Base", "Base.a", "Mode.ON"]`, with `Mode` an enum, gives
 * fields `{"Base.a"}` and types `{"Base", "Mode"}`.
 *
 * @param elementIds The result ids: `Type`, `Type.field`, `Enum`, or
 * `Enum.VALUE`.
 * @param schema The schema the tree is built from.
 * @returns The matched field ids and type names.
 */
export function groupElementIds(
	elementIds: string[],
	schema: GraphQLSchema,
): ElementMatches {
	const fieldIds = new Set<string>();
	const typeNames = new Set<string>();
	for (const elementId of elementIds) {
		const { typeName, memberName } = splitElementId(elementId);
		const parentType = schema.getType(typeName);
		if (memberName === undefined || isEnumType(parentType)) {
			typeNames.add(typeName);
			continue;
		}
		fieldIds.add(elementId);
	}

	return { fieldIds, typeNames };
}

/**
 * Finds the nodes of matched elements, and the ancestors that must be shown and
 * expanded to reveal them. A node matches when its type is a matched type, or
 * when it is a matched field of its parent node's type.
 *
 * @param nodes The searchable nodes.
 * @param matches The matched fields and types, from `groupElementIds`.
 * @returns The search; matched labels are highlighted whole, since the query
 * text rarely appears in them.
 */
export function searchTreeByElements(
	nodes: SchemaTreeNode[],
	matches: ElementMatches,
): TreeSearch {
	return revealMatchingNodes(
		nodes,
		(node, segment) => {
			if (matches.typeNames.has(node.type.name)) {
				return true;
			}
			if (segment.kind !== "field" || !node.parent) {
				return false;
			}
			const fieldId = toElementId(node.parent.type.name, segment.name);
			return matches.fieldIds.has(fieldId);
		},
		"",
		true,
	);
}
