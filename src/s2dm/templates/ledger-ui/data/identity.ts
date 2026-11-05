import { primaryKeyColumnsOf } from "@ledger-ui/data/schema";
import type { LedgerTable } from "@ledger-ui/data/types";

/**
 * Lists the columns that tell the records of a table apart. A column whose
 * name ends in `_uri` and that is not a foreign key holds the URIs of the
 * table's own records. It is not derived from the table name, because the
 * singular of a name such as "entities" can come out wrong.
 *
 * @param table - The table.
 * @returns The column that holds URIs of the table's own records, otherwise the
 *   whole primary key, otherwise the first column.
 */
export function identityColumnsOf(table: LedgerTable): string[] {
	const keyColumns = new Set(table.foreignKeys.map((key) => key.column));
	const ownUri = table.columns.find(
		(column) => column.name.endsWith("_uri") && !keyColumns.has(column.name),
	);
	if (ownUri) {
		return [ownUri.name];
	}
	const primaryKey = primaryKeyColumnsOf(table.columns);
	if (primaryKey.length > 0) {
		return primaryKey;
	}
	return table.columns.slice(0, 1).map((column) => column.name);
}

/**
 * Finds the identity column of the named table when one column is enough, so
 * a single value such as a URI can look the record up.
 *
 * @param tables - The tables of the ledger.
 * @param tableName - The name of the table.
 * @returns The one identity column, or `null` when no table has the name, or
 *   the table needs several columns or has none.
 */
export function singleIdentityColumnFor(
	tables: LedgerTable[],
	tableName: string,
): string | null {
	const table = tables.find((candidate) => candidate.name === tableName);
	if (!table) {
		return null;
	}
	const columns = identityColumnsOf(table);
	if (columns.length !== 1) {
		return null;
	}
	return columns[0];
}
