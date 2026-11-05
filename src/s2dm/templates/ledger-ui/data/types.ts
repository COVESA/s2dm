export type LedgerColumn = {
	name: string;
	declaredType: string;
	notNull: boolean;
	// 1-based position in the primary key, 0 when the column is not part of it.
	primaryKeyPosition: number;
};

export type LedgerForeignKey = {
	column: string;
	referencesTable: string;
	referencesColumn: string;
};

export type LedgerTable = {
	name: string;
	columns: LedgerColumn[];
	foreignKeys: LedgerForeignKey[];
	rowCount: number;
	activeCount: number | null;
};

export type LedgerValue = string | number | Uint8Array | null;

export type LedgerRecord = Record<string, LedgerValue>;

// Positional, unlike a record: a query may repeat a column name, and a keyed
// record keeps only the last of them.
export type LedgerCell = { column: string; value: LedgerValue };

export type QueryResult = {
	columns: string[];
	rows: LedgerValue[][];
	truncated: boolean;
};

export type LedgerSearchMatch = {
	table: string;
	result: QueryResult;
	total: number;
};
