import type { LedgerTable } from "@/ledger/types";

// The column holding URIs of the table's own records. Read from the schema
// rather than guessed from the table name, which mis-singularises "entities".
export function identityColumnOf(
	table: LedgerTable | undefined,
): string | null {
	if (!table) {
		return null;
	}
	const keyColumns = new Set(table.foreignKeys.map((key) => key.column));
	const ownUri = table.columns.find(
		(column) => column.name.endsWith("_uri") && !keyColumns.has(column.name),
	);
	const primaryKey = table.columns.find((column) => column.primaryKey);
	return ownUri?.name ?? primaryKey?.name ?? table.columns[0]?.name ?? null;
}

export function identityColumnFor(
	tables: LedgerTable[],
	table: string,
): string | null {
	return identityColumnOf(tables.find((candidate) => candidate.name === table));
}
