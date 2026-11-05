import {
	describeColumns,
	primaryKeyColumns,
	primaryKeyColumnsOf,
} from "@ledger-ui/data/schema";
import {
	compileSearchPattern,
	DEFAULT_SEARCH_OPTIONS,
	type SearchOptions,
} from "@ledger-ui/data/search";
import { columnPredicate } from "@ledger-ui/data/searchPredicate";
import {
	DEFAULT_ROW_LIMIT,
	quoteIdentifier,
	readAll,
} from "@ledger-ui/data/sql";
import type {
	LedgerColumn,
	LedgerRecord,
	LedgerValue,
	QueryResult,
} from "@ledger-ui/data/types";
import type { Database } from "sql.js";

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

/**
 * Writes the ORDER BY clause that sorts by the given columns, in their order.
 * Without the clause, SQLite makes no promise about row order.
 *
 * @param columns - The columns to sort by.
 * @returns The clause, or `""` when there are no columns.
 */
function orderByClause(columns: string[]): string {
	if (columns.length === 0) {
		return "";
	}
	const quoted = columns.map((column) => quoteIdentifier(column));
	return `ORDER BY ${quoted.join(", ")}`;
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
	// Ordered by the whole declared primary key, so a given row stays on the same
	// page. A table that declares none has no stable order.
	const order = primaryKeyColumnsOf(columns);
	const orderBy = orderByClause(order);
	// One row beyond the limit reveals whether more exist without a second query.
	return readAll(
		database,
		`SELECT * FROM ${quoteIdentifier(table)} ${conditions.where}
		 ${orderBy} LIMIT ? OFFSET ?`,
		[...conditions.params, limit + 1, offset],
		limit,
	);
}

/** Which page a row falls on, under the same primary-key ordering pages use. */
export function rowPageIndex(
	database: Database,
	table: string,
	record: LedgerRecord,
	pageSize: number,
): number {
	// Pages are ordered by the primary key, so only its columns can locate a row.
	const order = primaryKeyColumns(database, table);
	const values = order.map((column) => record[column] ?? null);
	if (order.length === 0 || values.includes(null)) {
		return 0;
	}
	// A row comes earlier when it equals the record on the leading key columns
	// and sorts before it on the next one. NULLs sort first in SQLite, so they
	// precede any value and must be counted.
	const clauses: string[] = [];
	const params: LedgerValue[] = [];
	for (const [index, column] of order.entries()) {
		const leading = order
			.slice(0, index)
			.map((leadingColumn) => `${quoteIdentifier(leadingColumn)} = ?`);
		const quoted = quoteIdentifier(column);
		const sortsBefore = `(${quoted} IS NULL OR ${quoted} < ?)`;
		clauses.push(`(${[...leading, sortsBefore].join(" AND ")})`);
		params.push(...values.slice(0, index + 1));
	}
	const { rows } = readAll(
		database,
		`SELECT COUNT(*) FROM ${quoteIdentifier(table)}
		 WHERE ${clauses.join(" OR ")}`,
		params,
	);
	return Math.floor(Number(rows[0]?.[0] ?? 0) / Math.max(1, pageSize));
}

/**
 * Reads the rows of a table that hold every one of the given column values.
 *
 * @param database - The database to read.
 * @param table - The table to read.
 * @param columnValues - The value that each row must hold, by column.
 * @param options - `limit` caps the rows, at `DEFAULT_ROW_LIMIT` by default.
 *   `orderBy` lists the columns that sort them.
 * @returns The matching rows.
 */
export function findRows(
	database: Database,
	table: string,
	columnValues: LedgerRecord,
	options: { limit?: number; orderBy?: string[] } = {},
): QueryResult {
	const entries = Object.entries(columnValues);
	const matches = entries.map(([column]) => `${quoteIdentifier(column)} = ?`);
	const values = entries.map(([, value]) => value);
	const orderBy = orderByClause(options.orderBy ?? []);
	return readAll(
		database,
		`SELECT * FROM ${quoteIdentifier(table)}
		 WHERE ${matches.join(" AND ")} ${orderBy} LIMIT ?`,
		[...values, options.limit ?? DEFAULT_ROW_LIMIT],
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
	const columns = describeColumns(database, table);
	return countMatches(database, table, columns, needle, options);
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
