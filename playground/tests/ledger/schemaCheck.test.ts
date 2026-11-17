import { MODL_SCHEMA } from "@ledger-ui/data/modlProfile";
import { readSchema } from "@ledger-ui/data/schema";
import {
	findSchemaIssues,
	MissingModlTablesError,
	requireModlTables,
} from "@ledger-ui/data/schemaCheck";
import type { LedgerTable } from "@ledger-ui/data/types";
import { describe, expect, it } from "vitest";
import { createDatabase, MODL_TABLES_SQL } from "./fixtures";

const modlDatabase = createDatabase(MODL_TABLES_SQL);
const MODL_TABLES = readSchema(modlDatabase);

function changeTable(
	name: string,
	change: (table: LedgerTable) => LedgerTable,
): LedgerTable[] {
	return MODL_TABLES.map((table) => {
		if (table.name !== name) {
			return table;
		}
		return change(table);
	});
}

function issueCodes(tables: LedgerTable[]): string[] {
	const issues = findSchemaIssues(tables);
	return issues.map((issue) => issue.code);
}

function rejectedTableNames(tables: LedgerTable[]): string[] {
	try {
		requireModlTables(tables);
	} catch (error) {
		if (error instanceof MissingModlTablesError) {
			return error.missingTables;
		}
		throw error;
	}
	return [];
}

describe("requireModlTables", () => {
	it("accepts a ModL export", () => {
		const names = rejectedTableNames(MODL_TABLES);

		expect(names).toEqual([]);
	});

	it("rejects a ledger without one ModL table", () => {
		const tables = MODL_TABLES.filter(
			(table) => table.name !== "contract_references",
		);

		expect(() => requireModlTables(tables)).toThrow(MissingModlTablesError);
		expect(rejectedTableNames(tables)).toEqual(["contract_references"]);
	});

	it("rejects a ledger without tables", () => {
		const expectedNames = MODL_SCHEMA.map((table) => table.name);

		const names = rejectedTableNames([]);

		expect(names).toEqual(expectedNames);
	});
});

describe("findSchemaIssues", () => {
	it("finds no issues in a ModL export", () => {
		const codes = issueCodes(MODL_TABLES);

		expect(codes).toEqual([]);
	});

	it("leaves a missing table to the open check", () => {
		const tables = MODL_TABLES.filter(
			(table) => table.name !== "contract_references",
		);

		const codes = issueCodes(tables);

		expect(codes).toEqual([]);
	});

	it("reports a missing column", () => {
		const tables = changeTable("bindings", (table) => {
			const columns = table.columns.filter(
				(column) => column.name !== "runtime_path",
			);
			return { ...table, columns };
		});

		const codes = issueCodes(tables);

		expect(codes).toEqual(["missing-column"]);
	});

	it("reports a table without a primary key", () => {
		const tables = changeTable("revision_aspects", (table) => {
			const columns = table.columns.map((column) => ({
				...column,
				primaryKeyPosition: 0,
			}));
			return { ...table, columns };
		});

		const codes = issueCodes(tables);

		expect(codes).toEqual(["wrong-primary-key"]);
	});

	it("reports a primary key in another column order", () => {
		const keyPositions: Record<string, number> = {
			revision_uri: 2,
			aspect_key: 1,
		};
		const tables = changeTable("revision_aspects", (table) => {
			const columns = table.columns.map((column) => {
				const primaryKeyPosition = keyPositions[column.name] ?? 0;
				return { ...column, primaryKeyPosition };
			});
			return { ...table, columns };
		});

		const codes = issueCodes(tables);

		expect(codes).toEqual(["wrong-primary-key"]);
	});

	it("reports a missing foreign key", () => {
		const tables = changeTable("bindings", (table) => ({
			...table,
			foreignKeys: [],
		}));

		const codes = issueCodes(tables);

		expect(codes).toEqual(["missing-foreign-key"]);
	});

	it("reports a foreign key to a table name in another case", () => {
		const tables = changeTable("bindings", (table) => {
			const foreignKeys = table.foreignKeys.map((key) => ({
				...key,
				referencesTable: "Contracts",
			}));
			return { ...table, foreignKeys };
		});

		const codes = issueCodes(tables);

		expect(codes).toEqual(["missing-foreign-key"]);
	});
});
