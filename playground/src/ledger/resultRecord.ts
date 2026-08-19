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

	if (candidates.length === 0) {
		return null;
	}

	const ranked = [...candidates].sort(
		(first, second) => second.columns.length - first.columns.length,
	);
	if (
		ranked.length > 1 &&
		ranked[0].columns.length === ranked[1].columns.length
	) {
		return null;
	}
	return ranked[0].name;
}

export function matchSingleRecordTable(
	result: QueryResult | null,
	tables: LedgerTable[],
): string | null {
	if (!result || result.rows.length !== 1) {
		return null;
	}
	return matchResultTable(result.columns, tables);
}
