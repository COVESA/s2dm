import {
	describeForeignKeys,
	orderTablesByDependency,
	primaryKeyColumns,
	primaryKeyColumnsOf,
	readSchema,
} from "@ledger-ui/data/schema";
import { describe, expect, it } from "vitest";
import {
	column,
	createDatabase,
	foreignKey,
	ledgerTable,
	MODL_TABLES_SQL,
} from "./fixtures";

describe("orderTablesByDependency", () => {
	it("puts each parent table before its children", () => {
		const contractKey = foreignKey("contract_uri", "contracts");
		const conceptKey = foreignKey("concept_uri", "concepts");
		const tables = [
			ledgerTable("bindings", [], [contractKey]),
			ledgerTable("contracts", [], [conceptKey]),
			ledgerTable("concepts", []),
		];

		const names = orderTablesByDependency(tables).map((table) => table.name);

		expect(names).toEqual(["concepts", "contracts", "bindings"]);
	});

	it("keeps tables without links in alphabetical order", () => {
		const tables = [
			ledgerTable("c", []),
			ledgerTable("a", []),
			ledgerTable("b", []),
		];

		const names = orderTablesByDependency(tables).map((table) => table.name);

		expect(names).toEqual(["a", "b", "c"]);
	});

	it("ignores a link from a table to itself", () => {
		const parentKey = foreignKey("parent_uri", "concepts", "concept_uri");
		const tables = [
			ledgerTable("concepts", [], [parentKey]),
			ledgerTable("bindings", []),
		];

		const names = orderTablesByDependency(tables).map((table) => table.name);

		expect(names).toEqual(["bindings", "concepts"]);
	});

	it("ignores a link to a missing table", () => {
		const missingKey = foreignKey("missing_id", "missing");
		const tables = [ledgerTable("b", [], [missingKey]), ledgerTable("a", [])];

		const names = orderTablesByDependency(tables).map((table) => table.name);

		expect(names).toEqual(["a", "b"]);
	});

	it("puts tables in a cycle at the end, in alphabetical order", () => {
		const keyToB = foreignKey("b_id", "b");
		const keyToC = foreignKey("c_id", "c");
		const tables = [
			ledgerTable("d", []),
			ledgerTable("c", [], [keyToB]),
			ledgerTable("b", [], [keyToC]),
			ledgerTable("a", []),
		];

		const names = orderTablesByDependency(tables).map((table) => table.name);

		expect(names).toEqual(["a", "d", "b", "c"]);
	});
});

describe("describeForeignKeys", () => {
	const ownerKey = foreignKey("owner_id", "owners", "id");
	const rowidKey = foreignKey("pair", "pairs", "rowid");

	it("reads a one-column key", () => {
		const database = createDatabase(`
			CREATE TABLE owners (id TEXT PRIMARY KEY);
			CREATE TABLE cars (owner_id TEXT REFERENCES owners (id));
		`);

		const keys = describeForeignKeys(database, "cars");

		expect(keys).toEqual([ownerKey]);
	});

	it("skips a key with several columns", () => {
		const database = createDatabase(`
			CREATE TABLE owners (id TEXT PRIMARY KEY);
			CREATE TABLE pairs (first TEXT, second TEXT, PRIMARY KEY (first, second));
			CREATE TABLE links (
				owner_id TEXT REFERENCES owners (id),
				pair_first TEXT,
				pair_second TEXT,
				FOREIGN KEY (pair_first, pair_second) REFERENCES pairs (first, second)
			);
		`);

		const keys = describeForeignKeys(database, "links");

		expect(keys).toEqual([ownerKey]);
	});

	it("uses the parent key when the link names no column", () => {
		const database = createDatabase(`
			CREATE TABLE owners (id TEXT PRIMARY KEY);
			CREATE TABLE cars (owner_id TEXT REFERENCES owners);
		`);

		const keys = describeForeignKeys(database, "cars");

		expect(keys).toEqual([ownerKey]);
	});

	it("uses rowid when the parent key has several columns", () => {
		const database = createDatabase(`
			CREATE TABLE pairs (first TEXT, second TEXT, PRIMARY KEY (first, second));
			CREATE TABLE links (pair TEXT REFERENCES pairs);
		`);

		const keys = describeForeignKeys(database, "links");

		expect(keys).toEqual([rowidKey]);
	});
});

describe("primaryKeyColumnsOf", () => {
	it("lists the key columns in key order", () => {
		const columns = [column("label"), column("second", 2), column("first", 1)];

		const keyColumns = primaryKeyColumnsOf(columns);

		expect(keyColumns).toEqual(["first", "second"]);
	});
});

describe("primaryKeyColumns", () => {
	it("lists the key columns in key order", () => {
		const database = createDatabase(`
			CREATE TABLE aspects (
				revision TEXT,
				aspect TEXT,
				label TEXT,
				PRIMARY KEY (aspect, revision)
			);
		`);

		const keyColumns = primaryKeyColumns(database, "aspects");

		expect(keyColumns).toEqual(["aspect", "revision"]);
	});

	it("is empty for a table without a key", () => {
		const database = createDatabase("CREATE TABLE notes (body TEXT);");

		const keyColumns = primaryKeyColumns(database, "notes");

		expect(keyColumns).toEqual([]);
	});
});

describe("readSchema", () => {
	it("orders the ModL tables with each parent first", () => {
		const database = createDatabase(MODL_TABLES_SQL);
		const parentChildPairs = [
			["concepts", "revisions"],
			["revisions", "contracts"],
			["contracts", "bindings"],
			["revisions", "revision_aspects"],
			["contracts", "contract_references"],
		];

		const names = readSchema(database).map((table) => table.name);

		expect(names).toHaveLength(6);
		for (const [parent, child] of parentChildPairs) {
			const parentPosition = names.indexOf(parent);
			const childPosition = names.indexOf(child);
			expect(parentPosition).toBeLessThan(childPosition);
		}
	});
});
