import { splitElementId, toElementId } from "@search-ui/utils/elementId";
import {
	matchesSearchTerm,
	normalizeSearchTerm,
} from "@search-ui/utils/textSearch";
import type { IntrospectionQuery } from "graphql";
import { fetchJson } from "@/utils/fetchJson";

/**
 * List the schema's elements, named the way `s2dm embeddings build` names them.
 *
 * @param schema - The schema introspection.
 * @returns Sorted ids: `Type`, `Type.field` and `Enum.VALUE`. Introspection types and the root
 *   query type are left out.
 */
function listElementIds(schema: IntrospectionQuery): string[] {
	const queryTypeName = schema.__schema.queryType?.name;
	const elementIds: string[] = [];
	for (const type of schema.__schema.types) {
		if (type.name.startsWith("__") || type.name === queryTypeName) {
			continue;
		}
		elementIds.push(type.name);
		let memberNames: string[] = [];
		if (type.kind === "OBJECT" || type.kind === "INTERFACE") {
			memberNames = type.fields.map((field) => field.name);
		} else if (type.kind === "INPUT_OBJECT") {
			memberNames = type.inputFields.map((inputField) => inputField.name);
		} else if (type.kind === "ENUM") {
			memberNames = type.enumValues.map((enumValue) => enumValue.name);
		}
		for (const memberName of memberNames) {
			const elementId = toElementId(type.name, memberName);
			elementIds.push(elementId);
		}
	}
	return elementIds.sort();
}

/**
 * Load the element ids of the site's schema.
 *
 * @param introspectionUrl - URL of the `introspection.json` written by `npm run doc`.
 * @returns Sorted element ids.
 * @throws Error when the file cannot be fetched.
 */
export async function loadElementIds(
	introspectionUrl: string,
): Promise<string[]> {
	const introspection = await fetchJson<{ data: IntrospectionQuery }>(
		introspectionUrl,
	);
	return listElementIds(introspection.data);
}

/**
 * Keep the elements whose own name contains the query, ignoring case.
 *
 * @param elementIds - Element ids, e.g. `Type.field`.
 * @param query - The search text.
 * @returns The matching ids, in their given order.
 */
export function filterElementIdsByName(
	elementIds: readonly string[],
	query: string,
): string[] {
	const normalizedQuery = normalizeSearchTerm(query);
	return elementIds.filter((elementId) => {
		const { typeName, memberName } = splitElementId(elementId);
		const elementName = memberName ?? typeName;
		return matchesSearchTerm(elementName, normalizedQuery);
	});
}
