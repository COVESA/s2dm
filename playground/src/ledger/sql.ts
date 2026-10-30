import type { Database } from "sql.js";
import type { LedgerValue, QueryResult } from "@/ledger/types";

export const DEFAULT_ROW_LIMIT = 1000;

export function quoteIdentifier(name: string): string {
	return `"${name.replaceAll('"', '""')}"`;
}

export function readAll(
	database: Database,
	sql: string,
	params?: LedgerValue[],
	rowLimit?: number,
): QueryResult {
	const statement = database.prepare(sql);
	try {
		if (params) {
			statement.bind(params);
		}
		// Unlike exec, a prepared statement reports column names for empty results.
		const columns = statement.getColumnNames();
		const rows: LedgerValue[][] = [];
		let truncated = false;
		while (statement.step()) {
			if (rowLimit !== undefined && rows.length >= rowLimit) {
				truncated = true;
				break;
			}
			rows.push(statement.get() as LedgerValue[]);
		}
		return { columns, rows, truncated };
	} finally {
		statement.free();
	}
}
