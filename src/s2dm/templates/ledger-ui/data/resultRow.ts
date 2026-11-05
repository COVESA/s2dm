import type {
	LedgerRecord,
	LedgerValue,
	QueryResult,
} from "@ledger-ui/data/types";

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

/**
 * Whether a page of rows holds the given record.
 *
 * @param page - The rows of the current page.
 * @param record - The record to look for.
 * @returns True when one row of the page has the record's value in every column.
 */
export function isRecordOnPage(
	page: QueryResult,
	record: LedgerRecord,
): boolean {
	const selectedValues = recordValues(record, page.columns);
	return page.rows.some((rowValues) => isSameRow(rowValues, selectedValues));
}
