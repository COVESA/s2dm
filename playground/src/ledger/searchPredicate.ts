import { MATCH_FUNCTION, type SearchPattern } from "@/ledger/search";
import type { LedgerValue } from "@/ledger/types";

export function escapeLikePattern(value: string): string {
	return value
		.replaceAll("\\", "\\\\")
		.replaceAll("%", "\\%")
		.replaceAll("_", "\\_");
}

/** The predicate matching one column against a compiled pattern, with its params. */
export function columnPredicate(
	quotedColumn: string,
	pattern: SearchPattern,
): { sql: string; params: LedgerValue[] } {
	const text = `CAST(${quotedColumn} AS TEXT)`;

	if (pattern.kind === "like") {
		return {
			sql: `${text} LIKE ? ESCAPE '\\'`,
			params: [`%${escapeLikePattern(pattern.value)}%`],
		};
	}
	if (pattern.kind === "instr") {
		return { sql: `instr(${text}, ?) > 0`, params: [pattern.value] };
	}
	return {
		sql: `${MATCH_FUNCTION}(?, ${text}, ?) = 1`,
		params: [pattern.source, pattern.flags],
	};
}
