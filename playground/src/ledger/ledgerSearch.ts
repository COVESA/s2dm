import type { Database } from "sql.js";
import { countSearchMatches, searchTable } from "@/ledger/rows";
import type { SearchOptions } from "@/ledger/search";
import type { LedgerSearchMatch, LedgerTable } from "@/ledger/types";

// One preview per table that matches, in chain order. The exact total costs a
// second scan, so it is only counted when the preview was truncated.
export function searchLedger(
	database: Database,
	// Already read and profiled by readSchema: building the list here again would
	// miss the fallback, and order a keyless file alphabetically instead.
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
