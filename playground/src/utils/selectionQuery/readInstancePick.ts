import {
	type DocumentNode,
	type FieldNode,
	type GraphQLSchema,
	TypeInfo,
	visit,
	visitWithTypeInfo,
} from "graphql";
import type { InstanceTagsResponse } from "@/api/types";
import {
	getFieldCoordinate,
	type InstancePickTarget,
} from "@/utils/selectionQuery/instanceTag";
import { readListedInstances } from "@/utils/selectionQuery/pick";

export type InstancePicks = {
	/** The instances listed on each instance tag field, by its coordinate. */
	instancesByTagField: Map<string, Set<string>>;
	/**
	 * The values listed on each dimension, by the coordinate of its instance tag
	 * field and then by dimension name.
	 */
	dimensionValuesByTagField: Map<string, Map<string, Set<string>>>;
};

export type PickState = {
	/** The names that the target's `@pick` lists; `undefined` without one. */
	listedNames: Set<string> | undefined;
	/** Whether the other `@pick` form is in use on the same instance tag field. */
	isOtherFormPicked: boolean;
};

type InstanceTagFieldVisit = {
	field: FieldNode;
	/** The field's coordinate when it is an instance tag field; `null` otherwise. */
	tagFieldCoordinate: string | null;
	/**
	 * The coordinate of the enclosing field when that is an instance tag field;
	 * `null` otherwise.
	 */
	enclosingTagFieldCoordinate: string | null;
};

/**
 * Walks every field of a query and tells, for each one, whether it or its
 * enclosing field is an instance tag field.
 *
 * @param schema The schema the query was validated against.
 * @param tagFields The instance tag fields, by `Type.field`.
 * @param document The parsed, validated selection query.
 * @param onField Called once per field, in document order.
 */
function visitInstanceTagFields(
	schema: GraphQLSchema,
	tagFields: InstanceTagsResponse,
	document: DocumentNode,
	onField: (fieldVisit: InstanceTagFieldVisit) => void,
): void {
	const typeInfo = new TypeInfo(schema);
	// The coordinate of each enclosing field that is an instance tag field;
	// `null` for any other field.
	const tagFieldStack: (string | null)[] = [];
	const visitor = visitWithTypeInfo(typeInfo, {
		Field: {
			enter(field: FieldNode) {
				const parentType = typeInfo.getParentType();
				const enclosingTagFieldCoordinate = tagFieldStack.at(-1) ?? null;
				let tagFieldCoordinate: string | null = null;
				if (parentType) {
					const coordinate = getFieldCoordinate(
						parentType.name,
						field.name.value,
					);
					if (tagFields[coordinate]) {
						tagFieldCoordinate = coordinate;
					}
				}
				tagFieldStack.push(tagFieldCoordinate);
				onField({ field, tagFieldCoordinate, enclosingTagFieldCoordinate });
			},
			leave() {
				tagFieldStack.pop();
			},
		},
	});
	visit(document, visitor);
}

/**
 * Reads the field-level `@pick` directives of a validated selection query. A
 * `@pick` belongs to the field's coordinate, not to its query path, so every
 * path that leads to the same field shares it. When two paths list different
 * names, the last one wins; the backend rejects such a query.
 *
 * @param schema The schema the query was validated against.
 * @param tagFields The instance tag fields, by `Type.field`.
 * @param document The parsed, validated selection query; `null` for empty
 * text.
 * @returns The listed instances and dimension values; empty when there is no
 * field-level `@pick`.
 */
export function readInstancePicks(
	schema: GraphQLSchema,
	tagFields: InstanceTagsResponse,
	document: DocumentNode | null,
): InstancePicks {
	const instancePicks: InstancePicks = {
		instancesByTagField: new Map(),
		dimensionValuesByTagField: new Map(),
	};
	if (!document) {
		return instancePicks;
	}

	visitInstanceTagFields(schema, tagFields, document, (fieldVisit) => {
		const { field, tagFieldCoordinate, enclosingTagFieldCoordinate } =
			fieldVisit;
		const listedNames = readListedInstances(field);
		if (!listedNames) {
			return;
		}

		if (tagFieldCoordinate) {
			instancePicks.instancesByTagField.set(tagFieldCoordinate, listedNames);
			return;
		}

		if (enclosingTagFieldCoordinate) {
			const valuesByDimension =
				instancePicks.dimensionValuesByTagField.get(
					enclosingTagFieldCoordinate,
				) ?? new Map<string, Set<string>>();
			valuesByDimension.set(field.name.value, listedNames);
			instancePicks.dimensionValuesByTagField.set(
				enclosingTagFieldCoordinate,
				valuesByDimension,
			);
		}
	});

	return instancePicks;
}

/**
 * Reads the `@pick` state of a target: what its own `@pick` lists, and
 * whether the other form is in use on the same instance tag field.
 *
 * @param instancePicks The field-level `@pick` choices of the query.
 * @param target Where the `@pick` goes.
 * @returns The listed names and the other-form check.
 */
export function readPickState(
	instancePicks: InstancePicks,
	target: InstancePickTarget,
): PickState {
	const { instancesByTagField, dimensionValuesByTagField } = instancePicks;
	const { tagFieldCoordinate, dimensionName } = target;
	const valuesByDimension = dimensionValuesByTagField.get(tagFieldCoordinate);
	if (dimensionName === null) {
		const listedInstances = instancesByTagField.get(tagFieldCoordinate);
		const hasDimensionPicks = valuesByDimension !== undefined;
		return {
			listedNames: listedInstances,
			isOtherFormPicked: hasDimensionPicks,
		};
	}

	const listedValues = valuesByDimension?.get(dimensionName);
	const hasTagFieldPick = instancesByTagField.has(tagFieldCoordinate);
	return { listedNames: listedValues, isOtherFormPicked: hasTagFieldPick };
}

/**
 * Finds every place in a query that selects the field of a `@pick` target:
 * the instance tag field, or one of its dimensions.
 *
 * @param schema The schema the query was validated against.
 * @param tagFields The instance tag fields, by `Type.field`.
 * @param document The parsed selection query.
 * @param target Where the `@pick` goes.
 * @returns The matching fields, in document order.
 */
export function findPickTargetFields(
	schema: GraphQLSchema,
	tagFields: InstanceTagsResponse,
	document: DocumentNode,
	target: InstancePickTarget,
): FieldNode[] {
	const { tagFieldCoordinate, dimensionName } = target;
	const matchingFields: FieldNode[] = [];
	visitInstanceTagFields(schema, tagFields, document, (fieldVisit) => {
		const { field } = fieldVisit;
		let isMatch = false;
		if (dimensionName === null) {
			isMatch = fieldVisit.tagFieldCoordinate === tagFieldCoordinate;
		} else {
			isMatch =
				fieldVisit.enclosingTagFieldCoordinate === tagFieldCoordinate &&
				field.name.value === dimensionName;
		}
		if (isMatch) {
			matchingFields.push(field);
		}
	});

	return matchingFields;
}
