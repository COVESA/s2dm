import { identityColumnsOf } from "@ledger-ui/data/identity";
import { findRows, toRecords } from "@ledger-ui/data/rows";
import type {
	LedgerRecord,
	LedgerTable,
	LedgerValue,
} from "@ledger-ui/data/types";
import type { Database } from "sql.js";

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

function sameValue(
	left: LedgerValue | undefined,
	right: LedgerValue | undefined,
): boolean {
	if (left == null || right == null) {
		return left == null && right == null;
	}
	if (left instanceof Uint8Array || right instanceof Uint8Array) {
		return String(left) === String(right);
	}
	return left === right;
}

/**
 * Finds the table that stores a row of a query result. A shape match only
 * shows that the query named a table's columns, which aliased constants can
 * do just as well, so the stored record is read back and compared value by
 * value.
 *
 * @param database - The database to read.
 * @param columns - The columns of the query result.
 * @param record - The row, by column.
 * @param tables - The tables of the ledger.
 * @returns The table that holds the row, or `null` when no table does.
 */
export function storedRecordTable(
	database: Database,
	columns: string[],
	record: LedgerRecord,
	tables: LedgerTable[],
): string | null {
	const candidate = matchResultTable(columns, tables);
	if (candidate === null) {
		return null;
	}

	const candidateTable = tables.find((table) => table.name === candidate);
	if (!candidateTable) {
		return null;
	}
	const identityColumns = identityColumnsOf(candidateTable);
	const hasIdentity =
		identityColumns.length > 0 &&
		identityColumns.every((column) => record[column] != null);
	if (!hasIdentity) {
		return null;
	}

	const identityEntries = identityColumns.map((column) => [
		column,
		record[column],
	]);
	const identity: LedgerRecord = Object.fromEntries(identityEntries);
	const result = findRows(database, candidate, identity, { limit: 1 });
	const [stored] = toRecords(result);
	if (!stored) {
		return null;
	}
	const holds = columns.every((column) =>
		sameValue(stored[column], record[column]),
	);
	return holds ? candidate : null;
}
