type RankedIndex = {
	index: number;
	score: number;
};

/**
 * Rank the rows of a vector table by cosine similarity to a query.
 *
 * Rows and query are normalized, so cosine similarity is their dot product. Equal scores keep
 * table order, matching the Python search.
 *
 * @param table - Row-major vectors, `dim` values per row.
 * @param dim - Values per vector.
 * @param query - The normalized query vector.
 * @param limit - Maximum number of rows to return.
 * @returns Up to `limit` rows, best first.
 * @throws Error when the query length differs from `dim`.
 */
export function rankTable(
	table: Float32Array,
	dim: number,
	query: Float32Array,
	limit: number,
): RankedIndex[] {
	if (query.length !== dim) {
		throw new Error(`Query has ${query.length} values; expected ${dim}.`);
	}
	const rowCount = table.length / dim;
	const ranked: RankedIndex[] = [];
	for (let index = 0; index < rowCount; index++) {
		const rowOffset = index * dim;
		let score = 0;
		for (let position = 0; position < dim; position++) {
			score += table[rowOffset + position] * query[position];
		}
		ranked.push({ index, score });
	}
	ranked.sort(
		(first, second) => second.score - first.score || first.index - second.index,
	);
	return ranked.slice(0, limit);
}
