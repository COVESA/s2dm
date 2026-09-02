import type { Database } from "sql.js";
import {
	describeColumns,
	orderingColumn,
	primaryKeyColumn,
} from "@/ledger/schema";
import {
	compileSearchPattern,
	DEFAULT_SEARCH_OPTIONS,
	type SearchOptions,
} from "@/ledger/search";
import { columnPredicate } from "@/ledger/searchPredicate";
import { DEFAULT_ROW_LIMIT, quoteIdentifier, readAll } from "@/ledger/sql";
import type {
	LedgerColumn,
	LedgerRecord,
	LedgerValue,
	QueryResult,
} from "@/ledger/types";

// Rows per page in the raw table view.
export const LEDGER_PAGE_SIZE = 50;

export type RowFilters = Record<string, string>;

// Every WHERE clause the row reads share, so search, filters and counts cannot
// diverge. Returns null when the table has no columns, meaning no such table.
function buildConditions(
	columns: LedgerColumn[],
	needle: string,
	filters: RowFilters,
	search: SearchOptions,
): { where: string; params: LedgerValue[] } | null {
	if (columns.length === 0) {
		return null;
	}

	const clauses: string[] = [];
	const params: LedgerValue[] = [];

	if (needle !== "") {
		const pattern = compileSearchPattern(needle, search);
		const perColumn = columns.map((column) => {
			const quoted = quoteIdentifier(column.name);
			return columnPredicate(quoted, pattern);
		});
		clauses.push(
			`(${perColumn.map((predicate) => predicate.sql).join(" OR ")})`,
		);
		for (const predicate of perColumn) {
			params.push(...predicate.params);
		}
	}

	const known = new Set(columns.map((column) => column.name));
	for (const [column, value] of Object.entries(filters)) {
		if (value !== "" && known.has(column)) {
			clauses.push(`${quoteIdentifier(column)} = ?`);
			params.push(value);
		}
	}

	return {
		where: clauses.length > 0 ? `WHERE ${clauses.join(" AND ")}` : "",
		params,
	};
}

export function searchTable(
	database: Database,
	table: string,
	needle: string,
	options: {
		limit?: number;
		offset?: number;
		filters?: RowFilters;
		search?: SearchOptions;
	} = {},
): QueryResult {
	const columns = describeColumns(database, table);
	const conditions = buildConditions(
		columns,
		needle,
		options.filters ?? {},
		options.search ?? DEFAULT_SEARCH_OPTIONS,
	);
	if (!conditions) {
		return { columns: [], rows: [], truncated: false };
	}

	const limit = options.limit ?? DEFAULT_ROW_LIMIT;
	const offset = options.offset ?? 0;
	// Ordered by the primary key, declared or from the profile, so a given row
	// stays on the same page. A table with neither has no stable order.
	const order = orderingColumn(table, columns);
	// One row beyond the limit reveals whether more exist without a second query.
	return readAll(
		database,
		`SELECT * FROM ${quoteIdentifier(table)} ${conditions.where}
		 ${order ? `ORDER BY ${quoteIdentifier(order)}` : ""} LIMIT ? OFFSET ?`,
		[...conditions.params, limit + 1, offset],
		limit,
	);
}

export function rowPageIndex(
	database: Database,
	table: string,
	record: LedgerRecord,
	pageSize: number,
): number {
	// Pages are ordered by the primary key, so only that column can locate a row.
	const order = primaryKeyColumn(database, table);
	const value = order === null ? undefined : record[order];
	if (order === null || value === undefined || value === null) {
		return 0;
	}
	// NULLs sort first in SQLite, so they precede any value and must be counted.
	const { rows } = readAll(
		database,
		`SELECT COUNT(*) FROM ${quoteIdentifier(table)}
		 WHERE ${quoteIdentifier(order)} IS NULL OR ${quoteIdentifier(order)} < ?`,
		[value],
	);
	return Math.floor(Number(rows[0]?.[0] ?? 0) / Math.max(1, pageSize));
}

export function findRows(
	database: Database,
	table: string,
	column: string,
	value: LedgerValue,
	options: { limit?: number; orderBy?: string } = {},
): QueryResult {
	// Without ORDER BY, SQLite makes no promise about row order.
	const order = options.orderBy
		? `ORDER BY ${quoteIdentifier(options.orderBy)}`
		: "";
	return readAll(
		database,
		`SELECT * FROM ${quoteIdentifier(table)}
		 WHERE ${quoteIdentifier(column)} = ? ${order} LIMIT ?`,
		[value, options.limit ?? DEFAULT_ROW_LIMIT],
	);
}

export function toRecord(row: LedgerValue[], columns: string[]): LedgerRecord {
	return Object.fromEntries(
		columns.map((column, index) => [column, row[index] ?? null]),
	);
}

export function toRecords(result: QueryResult): LedgerRecord[] {
	return result.rows.map((row) => toRecord(row, result.columns));
}

export function countSearchMatches(
	database: Database,
	table: string,
	needle: string,
	options: { filters?: RowFilters; search?: SearchOptions } = {},
): number {
	return countMatches(
		database,
		table,
		describeColumns(database, table),
		needle,
		options,
	);
}

// Takes the columns rather than reading them, so a caller that already holds
// them does not pay for a second PRAGMA.
function countMatches(
	database: Database,
	table: string,
	columns: LedgerColumn[],
	needle: string,
	options: { filters?: RowFilters; search?: SearchOptions },
): number {
	const conditions = buildConditions(
		columns,
		needle,
		options.filters ?? {},
		options.search ?? DEFAULT_SEARCH_OPTIONS,
	);
	if (!conditions) {
		return 0;
	}

	const { rows } = readAll(
		database,
		`SELECT COUNT(*) FROM ${quoteIdentifier(table)} ${conditions.where}`,
		conditions.params,
	);
	return Number(rows[0]?.[0] ?? 0);
}

export function listDistinctValues(
	database: Database,
	table: string,
	column: string,
	options: { limit?: number } = {},
): string[] {
	const columns = describeColumns(database, table);
	if (!columns.some((candidate) => candidate.name === column)) {
		return [];
	}

	const { rows } = readAll(
		database,
		`SELECT DISTINCT ${quoteIdentifier(column)} FROM ${quoteIdentifier(table)}
		 WHERE ${quoteIdentifier(column)} IS NOT NULL
		 ORDER BY ${quoteIdentifier(column)} LIMIT ?`,
		[options.limit ?? 100],
	);
	return rows.map(([value]) => String(value));
}
