import {
	type GraphQLNamedType,
	type GraphQLObjectType,
	getNamedType,
	isCompositeType,
	isInterfaceType,
	isLeafType,
	isObjectType,
	isUnionType,
} from "graphql";
import type { SelectionIndex } from "@/utils/selectionQuery/readSelection";

export type SchemaTreeSegment =
	| { kind: "field"; name: string }
	| { kind: "fragment"; typeName: string };

export type SchemaTreeNode = {
	key: string;
	segment: SchemaTreeSegment | null;
	parent: SchemaTreeNode | null;
	type: GraphQLNamedType;
	typeLabel: string;
	isRecursive: boolean;
	/** How many recursive nodes the path from the root to this node, itself included, passes through. */
	recursionDepth: number;
};

/**
 * The default recursion depth: how many recursive fields deep a branch can be
 * expanded.
 */
export const DEFAULT_RECURSION_DEPTH = 1;

/**
 * Builds the key of one path segment.
 *
 * @param segment The field or inline fragment segment.
 * @returns The field name, or `on <Type>` for an inline fragment.
 */
export function getSegmentKey(segment: SchemaTreeSegment): string {
	if (segment.kind === "field") {
		return segment.name;
	}

	return `on ${segment.typeName}`;
}

/**
 * Appends a segment to a parent path key.
 *
 * @param parentKey The parent's path key; the root's key is empty.
 * @param segment The child segment.
 * @returns The child's path key, for example `vehicle/cabin/on Door/isOpen`.
 */
export function joinPathKey(
	parentKey: string,
	segment: SchemaTreeSegment,
): string {
	const segmentKey = getSegmentKey(segment);
	if (!parentKey) {
		return segmentKey;
	}

	return `${parentKey}/${segmentKey}`;
}

/**
 * Lists the segment keys of a node's path from the root, for display.
 *
 * @param node The node.
 * @returns The segment keys, for example `["vehicle", "cabin", "on Door"]`;
 * empty for the root.
 */
export function getNodePathSegments(node: SchemaTreeNode): string[] {
	const chain = getNodeChain(node);
	return chain.flatMap((chainNode) => {
		if (!chainNode.segment) {
			return [];
		}

		return [getSegmentKey(chainNode.segment)];
	});
}

export function createRootNode(queryType: GraphQLObjectType): SchemaTreeNode {
	return {
		key: "",
		segment: null,
		parent: null,
		type: queryType,
		typeLabel: queryType.name,
		isRecursive: false,
		recursionDepth: 0,
	};
}

function hasAncestorType(node: SchemaTreeNode, typeName: string): boolean {
	let ancestor: SchemaTreeNode | null = node;
	while (ancestor) {
		if (ancestor.type.name === typeName) {
			return true;
		}
		ancestor = ancestor.parent;
	}

	return false;
}

function createChildNode(
	parent: SchemaTreeNode,
	segment: SchemaTreeSegment,
	type: GraphQLNamedType,
	typeLabel: string,
): SchemaTreeNode {
	const isRecursive =
		isCompositeType(type) && hasAncestorType(parent, type.name);
	const key = joinPathKey(parent.key, segment);
	let recursionDepth = parent.recursionDepth;
	if (isRecursive) {
		recursionDepth += 1;
	}

	return {
		key,
		segment,
		parent,
		type,
		typeLabel,
		isRecursive,
		recursionDepth,
	};
}

/**
 * Lists a node's children in schema order. Object and interface types yield
 * their fields; union types yield one inline fragment per member type.
 * Recursive nodes have children too; callers expand them lazily, one level at
 * a time.
 *
 * @param node The node to expand.
 * @returns The child nodes, or an empty list for leaves.
 */
export function getChildNodes(node: SchemaTreeNode): SchemaTreeNode[] {
	const { type } = node;
	if (isObjectType(type) || isInterfaceType(type)) {
		const fields = Object.values(type.getFields());
		return fields.map((field) => {
			const fieldType = getNamedType(field.type);
			const typeLabel = String(field.type);
			return createChildNode(
				node,
				{ kind: "field", name: field.name },
				fieldType,
				typeLabel,
			);
		});
	}

	if (isUnionType(type)) {
		const memberTypes = type.getTypes();
		return memberTypes.map((memberType) =>
			createChildNode(
				node,
				{ kind: "fragment", typeName: memberType.name },
				memberType,
				memberType.name,
			),
		);
	}

	return [];
}

export function isLeafNode(node: SchemaTreeNode): boolean {
	return isLeafType(node.type);
}

/**
 * Tells whether a node can be expanded. A recursive field within the depth
 * expands; one beyond it is shown but stays collapsed.
 *
 * @param node The node.
 * @param maxRecursionDepth How many recursive fields deep a branch can be
 * expanded.
 * @returns Whether the node has children and is within the depth.
 */
export function isExpandableNode(
	node: SchemaTreeNode,
	maxRecursionDepth: number,
): boolean {
	return !isLeafNode(node) && node.recursionDepth <= maxRecursionDepth;
}

/**
 * Lists a node's children that lie within a cycle depth: those whose path
 * passes through at most that many recursive fields. A limit equal to the
 * node's own recursion depth skips every recursive child.
 *
 * @param node The parent node.
 * @param maxRecursionDepth The highest recursion depth a child may have.
 * @returns The child nodes within the depth, in schema order.
 */
export function getChildNodesWithinDepth(
	node: SchemaTreeNode,
	maxRecursionDepth: number,
): SchemaTreeNode[] {
	const childNodes = getChildNodes(node);
	return childNodes.filter(
		(childNode) => childNode.recursionDepth <= maxRecursionDepth,
	);
}

/**
 * Tells whether a node has a leaf, itself included, without descending into
 * children beyond a cycle depth.
 *
 * @param node The node.
 * @param maxRecursionDepth The highest recursion depth a descendant may have.
 * @returns Whether the node is a leaf or has a leaf below it within the depth.
 */
function hasLeafWithinDepth(
	node: SchemaTreeNode,
	maxRecursionDepth: number,
): boolean {
	if (isLeafNode(node)) {
		return true;
	}

	const childNodes = getChildNodesWithinDepth(node, maxRecursionDepth);
	return childNodes.some((childNode) =>
		hasLeafWithinDepth(childNode, maxRecursionDepth),
	);
}

/**
 * Lists the children that selecting a node includes: children within a cycle
 * depth with at least one leaf below them.
 *
 * @param node The parent node.
 * @param maxRecursionDepth The highest recursion depth a descendant may have.
 * @returns The selectable child nodes, in schema order.
 */
export function getSelectableChildNodes(
	node: SchemaTreeNode,
	maxRecursionDepth: number,
): SchemaTreeNode[] {
	const childNodes = getChildNodesWithinDepth(node, maxRecursionDepth);
	return childNodes.filter((childNode) =>
		hasLeafWithinDepth(childNode, maxRecursionDepth),
	);
}

/**
 * Finds the selected nodes that pass through more recursive fields than a
 * cycle depth allows. Only selected paths are followed, and each branch stops
 * at its first such node.
 *
 * @param node The node to search below.
 * @param selection The index of the current text.
 * @param maxRecursionDepth The highest recursion depth a selected node may
 * have.
 * @returns The outermost selected nodes beyond the depth, in schema order.
 */
export function findNodesBeyondDepth(
	node: SchemaTreeNode,
	selection: SelectionIndex,
	maxRecursionDepth: number,
): SchemaTreeNode[] {
	const childNodes = getChildNodes(node);
	const selectedChildNodes = childNodes.filter((childNode) =>
		selection.occurrencesByKey.has(childNode.key),
	);
	return selectedChildNodes.flatMap((childNode) => {
		if (childNode.recursionDepth > maxRecursionDepth) {
			return [childNode];
		}

		return findNodesBeyondDepth(childNode, selection, maxRecursionDepth);
	});
}

/**
 * Lists the nodes from the root down to the given node.
 *
 * @param node The last node of the chain.
 * @returns The root first and the given node last.
 */
export function getNodeChain(node: SchemaTreeNode): SchemaTreeNode[] {
	const chain: SchemaTreeNode[] = [];
	let current: SchemaTreeNode | null = node;
	while (current) {
		chain.unshift(current);
		current = current.parent;
	}

	return chain;
}
