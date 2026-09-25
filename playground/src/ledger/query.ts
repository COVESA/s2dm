import type { Database } from "sql.js";
import { DEFAULT_ROW_LIMIT, readAll } from "@/ledger/sql";
import type { QueryResult } from "@/ledger/types";

export function isReadOnlyStatement(sql: string): boolean {
	// Comments are stripped first so a leading comment cannot disguise a write.
	const bare = sql.replace(/--[^\n]*/g, " ").replace(/\/\*[\s\S]*?\*\//g, " ");
	return /^\s*(select|with|explain)\b/i.test(bare);
}

export function runReadQuery(
	database: Database,
	sql: string,
	options: { limit?: number } = {},
): QueryResult {
	if (!isReadOnlyStatement(sql)) {
		throw new Error("Only SELECT, WITH and EXPLAIN queries are allowed.");
	}

	const result = readAll(
		database,
		sql,
		undefined,
		options.limit ?? DEFAULT_ROW_LIMIT,
	);
	if (result.columns.length === 0) {
		throw new Error("Only queries that return rows are supported.");
	}
	return result;
}
