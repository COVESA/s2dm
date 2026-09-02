import type { LedgerRecord, LedgerValue } from "@/ledger/types";

// Positional throughout: a repeated column name collapses in a keyed record, so
// comparing through one cannot even match the row it came from.
export function isSameRow(
	row: LedgerValue[],
	selected: LedgerValue[],
): boolean {
	if (row.length !== selected.length) {
		return false;
	}
	return row.every((value, index) => {
		const other = selected[index] ?? null;
		const left = value ?? null;
		if (left instanceof Uint8Array && other instanceof Uint8Array) {
			return left.byteLength === other.byteLength;
		}
		if (left instanceof Uint8Array || other instanceof Uint8Array) {
			return false;
		}
		return left === other;
	});
}

// For a selection held as a record, which is faithful whenever the columns are
// unique — every real table, and every query that matched one.
export function recordValues(
	record: LedgerRecord,
	columns: string[],
): LedgerValue[] {
	return columns.map((column) => record[column] ?? null);
}
