import type { LedgerRecord } from "@/ledger/types";

export type LedgerReference = {
	table: string;
	column: string;
	value: string;
};

// <namespace>/<type>/<id>, where <type> is a ledger table name.
const URI_PATTERN = /\/([A-Za-z_][A-Za-z0-9_]*)\/[^/]+$/;

export function referenceTableOf(
	value: unknown,
	tableNames: string[],
): string | null {
	if (typeof value !== "string") {
		return null;
	}
	const type = URI_PATTERN.exec(value)?.[1];
	return type && tableNames.includes(type) ? type : null;
}

/**
 * Records the row points at, one per distinct URI, ordered as the ledger's own
 * tables are so the actions read in chain order.
 */
export function findLedgerReferences(
	record: LedgerRecord,
	tableNames: string[],
): LedgerReference[] {
	const seen = new Set<string>();
	const found: LedgerReference[] = [];

	for (const [column, value] of Object.entries(record)) {
		const table = referenceTableOf(value, tableNames);
		if (!table) {
			continue;
		}
		const uri = String(value);
		if (seen.has(uri)) {
			continue;
		}
		seen.add(uri);
		found.push({ table, column, value: uri });
	}

	return found.sort(
		(first, second) =>
			tableNames.indexOf(first.table) - tableNames.indexOf(second.table),
	);
}
