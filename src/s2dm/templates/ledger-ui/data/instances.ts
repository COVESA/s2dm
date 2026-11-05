import type { LedgerValue } from "@ledger-ui/data/types";

export type InstanceDimension = { name: string; values: string[] };

function isJsonObject(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringList(value: unknown): value is string[] {
	return (
		Array.isArray(value) && value.every((item) => typeof item === "string")
	);
}

function parseJsonObject(value: LedgerValue): Record<string, unknown> | null {
	if (typeof value !== "string") {
		return null;
	}
	let parsed: unknown;
	try {
		parsed = JSON.parse(value);
	} catch {
		return null;
	}
	if (!isJsonObject(parsed)) {
		return null;
	}
	return parsed;
}

/**
 * Reads an `instances` value as its dimensions, in the order of the JSON object.
 *
 * @param value - The `instances` value of a concept.
 * @returns The dimensions, each with its values, or `null` when the value is not
 *   a JSON object of string lists.
 */
export function instanceDimensions(
	value: LedgerValue,
): InstanceDimension[] | null {
	const parsed = parseJsonObject(value);
	if (!parsed) {
		return null;
	}

	const dimensions: InstanceDimension[] = [];
	for (const [name, values] of Object.entries(parsed)) {
		if (!isStringList(values)) {
			return null;
		}
		dimensions.push({ name, values });
	}
	return dimensions;
}

/**
 * Reads an `instance_tags` value as the dimensions of the instance it names, in
 * the order of the JSON object. The entity URIs that key the tags are left out.
 *
 * @param value - The `instance_tags` value of a binding.
 * @returns The dimensions, each with its one value, or `null` when the value is
 *   not a JSON object of entity tags with string values.
 */
export function instanceTagDimensions(
	value: LedgerValue,
): InstanceDimension[] | null {
	const parsed = parseJsonObject(value);
	if (!parsed) {
		return null;
	}

	const dimensions: InstanceDimension[] = [];
	for (const tags of Object.values(parsed)) {
		if (!isJsonObject(tags)) {
			return null;
		}
		for (const [name, instance] of Object.entries(tags)) {
			if (typeof instance !== "string") {
				return null;
			}
			dimensions.push({ name, values: [instance] });
		}
	}
	return dimensions;
}

/**
 * Reads a value as dimensions by its shape: a JSON object of string lists, as in
 * `instances`, or a JSON object of entity tags, as in `instance_tags`.
 *
 * @param value - The value to read.
 * @returns The dimensions, or `null` when the value has neither shape.
 */
export function dimensionsOf(value: LedgerValue): InstanceDimension[] | null {
	const instances = instanceDimensions(value);
	if (instances !== null) {
		return instances;
	}
	return instanceTagDimensions(value);
}

/**
 * Writes one dimension as text, for example `dimension1: Front, Rear`.
 *
 * @param dimension - The dimension to write.
 * @returns The name of the dimension, followed by its values.
 */
export function formatDimension(dimension: InstanceDimension): string {
	const values = dimension.values.join(", ");
	return `${dimension.name}: ${values}`;
}
