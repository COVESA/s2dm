import { MODL_SCHEMA, type ModlTableSchema } from "@ledger-ui/data/modlProfile";
import { primaryKeyColumnsOf } from "@ledger-ui/data/schema";
import type { LedgerForeignKey, LedgerTable } from "@ledger-ui/data/types";

export type SchemaIssueCode =
	| "missing-column"
	| "wrong-primary-key"
	| "missing-foreign-key";

export type SchemaIssue = {
	code: SchemaIssueCode;
	message: string;
};

/** A ledger that lacks one or more ModL tables. Such a ledger does not open. */
export class MissingModlTablesError extends Error {
	readonly missingTables: string[];

	constructor(missingTables: string[]) {
		const tableList = missingTables.join(", ");
		super(`The ledger is missing these ModL tables: ${tableList}.`);
		this.name = "MissingModlTablesError";
		this.missingTables = missingTables;
	}
}

/**
 * Checks that a ledger has every ModL table.
 *
 * @param tables - The tables as read from the database.
 * @throws MissingModlTablesError when one or more ModL tables are missing.
 */
export function requireModlTables(tables: LedgerTable[]): void {
	const tableNames = new Set(tables.map((table) => table.name));
	const missingTables = MODL_SCHEMA.filter(
		(expected) => !tableNames.has(expected.name),
	).map((expected) => expected.name);
	if (missingTables.length > 0) {
		throw new MissingModlTablesError(missingTables);
	}
}

/**
 * Compares the tables of a ledger with the ModL schema. A missing table gives
 * no issue, because such a ledger does not open.
 *
 * @param tables - The tables as read from the database.
 * @returns One issue per missing column, wrong primary key or missing foreign
 *   key. Empty when the ledger matches the ModL schema.
 */
export function findSchemaIssues(tables: LedgerTable[]): SchemaIssue[] {
	const issues: SchemaIssue[] = [];
	for (const expected of MODL_SCHEMA) {
		const table = tables.find((candidate) => candidate.name === expected.name);
		if (!table) {
			continue;
		}
		const columnIssues = findColumnIssues(expected, table);
		const primaryKeyIssues = findPrimaryKeyIssues(expected, table);
		const foreignKeyIssues = findForeignKeyIssues(expected, table);
		issues.push(...columnIssues, ...primaryKeyIssues, ...foreignKeyIssues);
	}
	return issues;
}

function findColumnIssues(
	expected: ModlTableSchema,
	table: LedgerTable,
): SchemaIssue[] {
	const columnNames = table.columns.map((column) => column.name);
	const present = new Set(columnNames);
	const missing = expected.columns.filter((column) => !present.has(column));
	return missing.map((column): SchemaIssue => {
		const message = `Column ${table.name}.${column} is missing.`;
		return { code: "missing-column", message };
	});
}

function findPrimaryKeyIssues(
	expected: ModlTableSchema,
	table: LedgerTable,
): SchemaIssue[] {
	const declared = primaryKeyColumnsOf(table.columns);
	const isExpectedKey =
		declared.length === expected.primaryKey.length &&
		declared.every((column, index) => column === expected.primaryKey[index]);
	if (isExpectedKey) {
		return [];
	}

	const expectedText = expected.primaryKey.join(", ");
	let message = `${table.name} has no primary key. ModL expects ${expectedText}.`;
	if (declared.length > 0) {
		const declaredText = declared.join(", ");
		message = `The primary key of ${table.name} is ${declaredText}. ModL expects ${expectedText}.`;
	}
	return [{ code: "wrong-primary-key", message }];
}

function findForeignKeyIssues(
	expected: ModlTableSchema,
	table: LedgerTable,
): SchemaIssue[] {
	const missing = expected.foreignKeys.filter(
		(key) =>
			!table.foreignKeys.some((declared) => isSameForeignKey(declared, key)),
	);
	return missing.map((key): SchemaIssue => {
		const message = `Foreign key from ${table.name}.${key.column} to ${key.referencesTable}.${key.referencesColumn} is missing.`;
		return { code: "missing-foreign-key", message };
	});
}

function isSameForeignKey(
	first: LedgerForeignKey,
	second: LedgerForeignKey,
): boolean {
	return (
		first.column === second.column &&
		first.referencesTable === second.referencesTable &&
		first.referencesColumn === second.referencesColumn
	);
}
