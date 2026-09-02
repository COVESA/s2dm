import type { LedgerTable, QueryResult } from "@/ledger/types";

// Exact column count, not containment: a join would match the widest table.
export function matchResultTable(
	columns: string[],
	tables: LedgerTable[],
): string | null {
	const available = new Set(columns);
	const candidates = tables.filter(
		(table) =>
			table.columns.length > 0 &&
			table.columns.length === columns.length &&
			table.columns.every((column) => available.has(column.name)),
	);

	// One candidate, or none: an ambiguous shape identifies no table.
	const only = candidates.length === 1 ? candidates[0] : undefined;
	return only?.name ?? null;
}

export function tableToAutoOpen(
	result: QueryResult | null,
	tables: LedgerTable[],
): string | null {
	if (!result || result.rows.length !== 1) {
		return null;
	}
	return matchResultTable(result.columns, tables);
}
