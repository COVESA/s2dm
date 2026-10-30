import type { InstanceTagsResponse } from "@/api/types";
import type { SchemaTreeNode } from "@/utils/selectionQuery/schemaTree";

export type InstancePickTarget = {
	/** The instance tag field's node; for a dimension, the dimension's parent. */
	tagFieldNode: SchemaTreeNode;
	tagFieldCoordinate: string;
	/** The picked dimension; `null` when `@pick` goes on the instance tag field. */
	dimensionName: string | null;
	pickableNames: string[];
};

/**
 * Joins a type name and a field name, for example `Type.field`. The result
 * is the same wherever the field appears in the query.
 *
 * @param typeName The type that has the field.
 * @param fieldName The field's name.
 * @returns The joined name.
 */
export function getFieldCoordinate(
	typeName: string,
	fieldName: string,
): string {
	return `${typeName}.${fieldName}`;
}

function getNodeCoordinate(node: SchemaTreeNode): string | null {
	const { segment, parent } = node;
	if (segment?.kind !== "field" || !parent) {
		return null;
	}

	return getFieldCoordinate(parent.type.name, segment.name);
}

/**
 * Resolves where the `@pick` of a tree node goes: on an instance tag field, or
 * on one of its dimensions.
 *
 * @param node The tree node.
 * @param tagFields The instance tag fields, by `Type.field`.
 * @returns The target; `null` when the node is neither.
 */
export function getInstancePickTarget(
	node: SchemaTreeNode,
	tagFields: InstanceTagsResponse,
): InstancePickTarget | null {
	const { segment, parent } = node;
	if (segment?.kind !== "field" || !parent) {
		return null;
	}

	const coordinate = getFieldCoordinate(parent.type.name, segment.name);
	const instances = tagFields[coordinate]?.instances;
	if (instances) {
		return {
			tagFieldNode: node,
			tagFieldCoordinate: coordinate,
			dimensionName: null,
			pickableNames: instances,
		};
	}

	const parentCoordinate = getNodeCoordinate(parent);
	if (!parentCoordinate) {
		return null;
	}

	const dimensionValues =
		tagFields[parentCoordinate]?.dimensions[segment.name];
	if (!dimensionValues) {
		return null;
	}

	return {
		tagFieldNode: parent,
		tagFieldCoordinate: parentCoordinate,
		dimensionName: segment.name,
		pickableNames: dimensionValues,
	};
}
