import type { Database } from "sql.js";
import {
	compileSearchPattern,
	DEFAULT_SEARCH_OPTIONS,
	type SearchOptions,
} from "@/ledger/search";
import { columnPredicate } from "@/ledger/searchPredicate";

export { escapeLikePattern } from "@/ledger/searchPredicate";

import type {
	LedgerColumn,
	LedgerForeignKey,
	LedgerRecord,
	LedgerSearchMatch,
	LedgerTable,
	LedgerValue,
	QueryResult,
} from "@/ledger/types";

export const DEFAULT_ROW_LIMIT = 1000;

export function quoteIdentifier(name: string): string {
	return `"${name.replaceAll('"', '""')}"`;
}

function readAll(
	database: Database,
	sql: string,
	params?: LedgerValue[],
): QueryResult {
	const statement = database.prepare(sql);
	try {
		if (params) {
			statement.bind(params);
		}
		// Unlike exec, a prepared statement reports column names for empty results.
		const columns = statement.getColumnNames();
		const rows: LedgerValue[][] = [];
		while (statement.step()) {
			rows.push(statement.get() as LedgerValue[]);
		}
		return { columns, rows, truncated: false };
	} finally {
		statement.free();
	}
}

function capRows(result: QueryResult, limit: number): QueryResult {
	const truncated = result.rows.length > limit;
	return {
		columns: result.columns,
		rows: truncated ? result.rows.slice(0, limit) : result.rows,
		truncated,
	};
}

export function listTableNames(database: Database): string[] {
	// SQLite reserves the sqlite_ prefix for its own tables, such as sqlite_stat1.
	const { rows } = readAll(
		database,
		`SELECT name FROM sqlite_master
		 WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
		 ORDER BY name`,
	);
	return rows.map(([name]) => String(name));
}

export function describeColumns(
	database: Database,
	table: string,
): LedgerColumn[] {
	const { rows } = readAll(
		database,
		`PRAGMA table_info(${quoteIdentifier(table)})`,
	);
	return rows.map(([, name, declaredType, notNull, , primaryKey]) => ({
		name: String(name),
		declaredType: declaredType === null ? "" : String(declaredType),
		notNull: Number(notNull) === 1,
		primaryKey: Number(primaryKey) > 0,
	}));
}

export function describeForeignKeys(
	database: Database,
	table: string,
): LedgerForeignKey[] {
	const { rows } = readAll(
		database,
		`PRAGMA foreign_key_list(${quoteIdentifier(table)})`,
	);
	return rows.map(([, , referencesTable, column, referencesColumn]) => {
		const target = String(referencesTable);
		return {
			column: String(column),
			referencesTable: target,
			// SQLite reports no target column when the key omits one, meaning it
			// resolves to the parent's primary key.
			referencesColumn:
				referencesColumn === null
					? (primaryKeyColumn(database, target) ?? "rowid")
					: String(referencesColumn),
		};
	});
}

export function countRows(
	database: Database,
	table: string,
	options: { filters?: RowFilters; search?: SearchOptions } = {},
): number {
	return countSearchMatches(database, table, "", options);
}

export function orderTablesByDependency<
	T extends { name: string; foreignKeys: LedgerForeignKey[] },
>(tables: T[]): T[] {
	const present = new Set(tables.map((table) => table.name));
	const dependencies = (table: T) =>
		table.foreignKeys
			.map((key) => key.referencesTable)
			.filter((target) => target !== table.name && present.has(target));

	const remaining = [...tables].sort((first, second) =>
		first.name.localeCompare(second.name),
	);
	const ordered: T[] = [];

	while (remaining.length > 0) {
		const index = remaining.findIndex((table) =>
			dependencies(table).every(
				(target) => !remaining.some((pending) => pending.name === target),
			),
		);
		if (index === -1) {
			break;
		}
		ordered.push(...remaining.splice(index, 1));
	}

	return [...ordered, ...remaining];
}

export function readSchema(database: Database): LedgerTable[] {
	return orderTablesByDependency(
		listTableNames(database).map((name) => {
			const columns = describeColumns(database, name);
			const hasStatus = columns.some((column) => column.name === "status");
			return {
				name,
				columns,
				foreignKeys: describeForeignKeys(database, name),
				rowCount: countRows(database, name),
				activeCount: hasStatus
					? countRowsWhere(database, name, "status", "ACTIVE")
					: null,
			};
		}),
	);
}

export function readTablePage(
	database: Database,
	table: string,
	options: {
		limit?: number;
		offset?: number;
		filters?: RowFilters;
		search?: SearchOptions;
	} = {},
): QueryResult {
	return searchTable(database, table, "", options);
}

export type RowFilters = Record<string, string>;

function buildConditions(
	database: Database,
	table: string,
	needle: string,
	filters: RowFilters,
	search: SearchOptions,
): { where: string; params: LedgerValue[] } | null {
	const columns = describeColumns(database, table);
	if (columns.length === 0) {
		return null;
	}

	const clauses: string[] = [];
	const params: LedgerValue[] = [];

	if (needle !== "") {
		const pattern = compileSearchPattern(needle, search);
		const perColumn = columns.map((column) =>
			columnPredicate(quoteIdentifier(column.name), pattern),
		);
		clauses.push(`(${perColumn.map((one) => one.sql).join(" OR ")})`);
		for (const one of perColumn) {
			params.push(...one.params);
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
	const conditions = buildConditions(
		database,
		table,
		needle,
		options.filters ?? {},
		options.search ?? DEFAULT_SEARCH_OPTIONS,
	);
	if (!conditions) {
		return { columns: [], rows: [], truncated: false };
	}

	const limit = options.limit ?? DEFAULT_ROW_LIMIT;
	const offset = options.offset ?? 0;
	// Ordered by primary key so a given row is always on the same page.
	const order = primaryKeyColumn(database, table);
	// One row beyond the limit reveals whether more exist without a second query.
	const result = readAll(
		database,
		`SELECT * FROM ${quoteIdentifier(table)} ${conditions.where}
		 ${order ? `ORDER BY ${quoteIdentifier(order)}` : ""} LIMIT ? OFFSET ?`,
		[...conditions.params, limit + 1, offset],
	);
	return capRows(result, limit);
}

export function primaryKeyColumn(
	database: Database,
	table: string,
): string | null {
	return (
		describeColumns(database, table).find((column) => column.primaryKey)
			?.name ?? null
	);
}

/** Which page a row falls on, given the same ordering readTablePage uses. */
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

export function countRowsWhere(
	database: Database,
	table: string,
	column: string,
	value: LedgerValue,
): number {
	const { rows } = readAll(
		database,
		`SELECT COUNT(*) FROM ${quoteIdentifier(table)}
		 WHERE ${quoteIdentifier(column)} = ?`,
		[value],
	);
	return Number(rows[0]?.[0] ?? 0);
}

export function toRecords(result: QueryResult): LedgerRecord[] {
	return result.rows.map((row) =>
		Object.fromEntries(
			result.columns.map((column, index) => [column, row[index] ?? null]),
		),
	);
}

export function countSearchMatches(
	database: Database,
	table: string,
	needle: string,
	options: { filters?: RowFilters; search?: SearchOptions } = {},
): number {
	const conditions = buildConditions(
		database,
		table,
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

export function searchLedger(
	database: Database,
	needle: string,
	options: { limit?: number; search?: SearchOptions } = {},
): LedgerSearchMatch[] {
	const tables = orderTablesByDependency(
		listTableNames(database).map((name) => ({
			name,
			foreignKeys: describeForeignKeys(database, name),
		})),
	);

	return tables
		.map((table) => {
			const result = searchTable(database, table.name, needle, options);
			return {
				table: table.name,
				result,
				// A preview that was not truncated has already counted the matches,
				// which spares a second full scan of the table.
				total: result.truncated
					? countSearchMatches(database, table.name, needle, {
							search: options.search,
						})
					: result.rows.length,
			};
		})
		.filter((match) => match.result.rows.length > 0);
}

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

	const limit = options.limit ?? DEFAULT_ROW_LIMIT;
	const statement = database.prepare(sql);
	try {
		const columns = statement.getColumnNames();
		if (columns.length === 0) {
			throw new Error("Only queries that return rows are supported.");
		}
		const rows: LedgerValue[][] = [];
		let truncated = false;
		while (statement.step()) {
			if (rows.length >= limit) {
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
