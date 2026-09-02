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
		const rowValue = value ?? null;
		const selectedValue = selected[index] ?? null;
		if (rowValue instanceof Uint8Array && selectedValue instanceof Uint8Array) {
			// By content, not length alone. Reached only for a row whose earlier
			// columns already matched, and it stops at the first differing byte.
			return (
				rowValue.byteLength === selectedValue.byteLength &&
				rowValue.every((byte, position) => byte === selectedValue[position])
			);
		}
		if (rowValue instanceof Uint8Array || selectedValue instanceof Uint8Array) {
			return false;
		}
		return rowValue === selectedValue;
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
