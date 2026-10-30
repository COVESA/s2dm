export type ElementIdParts = {
	typeName: string;
	/** The field, input field or enum value; absent when the id names a type. */
	memberName?: string;
};

/**
 * Build the id of a type's member, the way `s2dm embeddings build` names it.
 *
 * @param typeName - The type's name.
 * @param memberName - The field, input field or enum value.
 * @returns The id, `Type.member`.
 */
export function toElementId(typeName: string, memberName: string): string {
	return `${typeName}.${memberName}`;
}

/**
 * Split an element id into its type and member names.
 *
 * @param elementId - `Type` or `Type.member`.
 * @returns The type name, and the member name when the id names a member.
 */
export function splitElementId(elementId: string): ElementIdParts {
	const separatorIndex = elementId.indexOf(".");
	if (separatorIndex === -1) {
		return { typeName: elementId };
	}
	return {
		typeName: elementId.slice(0, separatorIndex),
		memberName: elementId.slice(separatorIndex + 1),
	};
}
