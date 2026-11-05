import { countSearchMatches, searchTable } from "@ledger-ui/data/rows";
import type { SearchOptions } from "@ledger-ui/data/search";
import type { LedgerSearchMatch, LedgerTable } from "@ledger-ui/data/types";
import type { Database } from "sql.js";

/**
 * Searches each table for a needle.
 *
 * @param database - The database to search.
 * @param tables - The tables to search. The matches keep their order.
 * @param needle - The text to look for.
 * @param options - `limit` caps the preview rows of each table. `search` sets
 *   how the needle matches.
 * @returns One match per table that has matching rows, with a preview of the
 *   rows and the total number of matches.
 */
export function searchLedger(
	database: Database,
	tables: LedgerTable[],
	needle: string,
	options: { limit?: number; search?: SearchOptions } = {},
): LedgerSearchMatch[] {
	return tables
		.map((table) => {
			const result = searchTable(database, table.name, needle, options);
			return {
				table: table.name,
				result,
				// A preview that was not truncated has already counted the matches,
				// which spares a second full scan of the table.
				total: result.truncated
					? countSearchMatches(database, table.name, needle, {
							search: options.search,
						})
					: result.rows.length,
			};
		})
		.filter((match) => match.result.rows.length > 0);
}
