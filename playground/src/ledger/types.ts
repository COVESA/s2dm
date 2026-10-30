export type LedgerColumn = {
	name: string;
	declaredType: string;
	notNull: boolean;
	primaryKey: boolean;
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
