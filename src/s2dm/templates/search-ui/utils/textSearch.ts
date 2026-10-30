/**
 * Prepare typed search text for matching.
 *
 * @param term - The typed text.
 * @returns The text, trimmed and lower-cased.
 */
export function normalizeSearchTerm(term: string): string {
	const trimmedTerm = term.trim();
	return trimmedTerm.toLowerCase();
}

/**
 * Check whether a text contains a search term, ignoring case.
 *
 * @param text - The text to search in, e.g. a name.
 * @param normalizedTerm - The term, from `normalizeSearchTerm`.
 * @returns Whether the text contains the term.
 */
export function matchesSearchTerm(
	text: string,
	normalizedTerm: string,
): boolean {
	const normalizedText = text.toLowerCase();
	return normalizedText.includes(normalizedTerm);
}
