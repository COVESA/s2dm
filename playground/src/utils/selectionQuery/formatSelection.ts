/**
 * Formats a selection query with Prettier, which keeps comments. Prettier is
 * loaded on first use so it stays out of the initial bundle.
 *
 * @param selectionQuery The selection query text.
 * @returns The formatted text, or the input unchanged when formatting fails.
 */
export async function formatSelection(selectionQuery: string): Promise<string> {
	try {
		const [prettier, graphqlPlugin] = await Promise.all([
			import("prettier/standalone"),
			import("prettier/plugins/graphql"),
		]);
		return await prettier.format(selectionQuery, {
			parser: "graphql",
			plugins: [graphqlPlugin],
		});
	} catch (error) {
		console.error("Selection query formatting failed:", error);
		return selectionQuery;
	}
}
