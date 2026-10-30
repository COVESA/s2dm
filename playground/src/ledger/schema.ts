import type { Database } from "sql.js";
import {
	ACTIVE_STATUS,
	applyModlProfile,
	MODL_TABLES,
	STATUS_COLUMN,
} from "@/ledger/modlProfile";
import { quoteIdentifier, readAll } from "@/ledger/sql";
import type {
	LedgerColumn,
	LedgerForeignKey,
	LedgerTable,
	LedgerValue,
} from "@/ledger/types";

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
		declaredType: String(declaredType ?? ""),
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
	// One row per column, grouped by id. A composite key is skipped rather than
	// read as several single-column keys, which would join on part of it.
	const byConstraint = new Map<string, LedgerValue[][]>();
	for (const row of rows) {
		const id = String(row[0]);
		byConstraint.set(id, [...(byConstraint.get(id) ?? []), row]);
	}

	const keys: LedgerForeignKey[] = [];
	for (const group of byConstraint.values()) {
		const row = group[0];
		if (group.length !== 1 || !row) {
			continue;
		}
		const [, , referencesTable, column, referencesColumn] = row;
		const target = String(referencesTable);
		keys.push({
			column: String(column),
			referencesTable: target,
			// SQLite reports no target column when the key omits one, meaning it
			// resolves to the parent's primary key.
			referencesColumn:
				referencesColumn === null
					? (primaryKeyColumn(database, target) ?? "rowid")
					: String(referencesColumn),
		});
	}
	return keys;
}

// Kahn's algorithm: parents before children, alphabetical among equals. Any
// table still pending at the end is in a cycle, and keeps its alphabetical place.
export function orderTablesByDependency<
	T extends { name: string; foreignKeys: LedgerForeignKey[] },
>(tables: T[]): T[] {
	const present = new Set(tables.map((table) => table.name));
	const sorted = [...tables].sort((first, second) =>
		first.name.localeCompare(second.name),
	);

	const pending = new Map<string, Set<string>>();
	for (const table of sorted) {
		pending.set(
			table.name,
			new Set(
				table.foreignKeys
					.map((key) => key.referencesTable)
					.filter((target) => target !== table.name && present.has(target)),
			),
		);
	}

	const ordered: T[] = [];
	let progressed = true;
	while (progressed) {
		progressed = false;
		for (const table of sorted) {
			const waitingFor = pending.get(table.name);
			if (!waitingFor || waitingFor.size > 0) {
				continue;
			}
			pending.delete(table.name);
			ordered.push(table);
			progressed = true;
			for (const rest of pending.values()) {
				rest.delete(table.name);
			}
		}
	}

	// Whatever is still pending is in a cycle, and keeps its alphabetical place.
	return [...ordered, ...sorted.filter((table) => pending.has(table.name))];
}

export function primaryKeyColumn(
	database: Database,
	table: string,
): string | null {
	return orderingColumn(table, describeColumns(database, table));
}

export function orderingColumn(
	table: string,
	columns: LedgerColumn[],
): string | null {
	const declared = columns.find((column) => column.primaryKey)?.name;
	if (declared) {
		return declared;
	}
	// Read directly rather than through readSchema, so the profile applies here too.
	const profile = MODL_TABLES[table];
	return profile && columns.some((column) => column.name === profile.primaryKey)
		? profile.primaryKey
		: null;
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

// Both counts in one pass: the table is scanned once either way.
function countRows(
	database: Database,
	table: string,
	statusColumn: string | null,
): { total: number; active: number | null } {
	const active = statusColumn
		? `, SUM(CASE WHEN ${quoteIdentifier(statusColumn)} = ? THEN 1 ELSE 0 END)`
		: "";
	const { rows } = readAll(
		database,
		`SELECT COUNT(*)${active} FROM ${quoteIdentifier(table)}`,
		statusColumn ? [ACTIVE_STATUS] : undefined,
	);
	return {
		total: Number(rows[0]?.[0] ?? 0),
		active: statusColumn ? Number(rows[0]?.[1] ?? 0) : null,
	};
}

export function readSchema(database: Database): LedgerTable[] {
	// The profile is applied before ordering, which reads the keys it supplies.
	return orderTablesByDependency(
		applyModlProfile(
			listTableNames(database).map((name) => {
				const columns = describeColumns(database, name);
				const statusColumn = columns.some(
					(column) => column.name === STATUS_COLUMN,
				)
					? STATUS_COLUMN
					: null;
				const counted = countRows(database, name, statusColumn);
				return {
					name,
					columns,
					foreignKeys: describeForeignKeys(database, name),
					rowCount: counted.total,
					activeCount: counted.active,
				};
			}),
		),
	);
}
