import {
	countSearchMatches,
	rowPageIndex,
	searchTable,
	toRecords,
} from "@ledger-ui/data/rows";
import { describe, expect, it } from "vitest";
import { createDatabase, MODL_TABLES_SQL } from "./fixtures";

const PAGE_SIZE = 2;

const ASPECTS_SQL = `
	CREATE TABLE aspects (revision TEXT, aspect TEXT, PRIMARY KEY (revision, aspect));
	INSERT INTO aspects VALUES
		('r1', 'a'), ('r1', 'b'), ('r2', 'a'), ('r2', 'b'), ('r2', 'c');
`;

describe("rowPageIndex", () => {
	it("finds the page of a row with a one-column key", () => {
		const database = createDatabase(`
			CREATE TABLE items (serial INTEGER PRIMARY KEY, label TEXT);
			INSERT INTO items VALUES (1, 'a'), (2, 'b'), (3, 'c'), (4, 'd'), (5, 'e');
		`);
		const record = { serial: 4, label: "d" };

		const page = rowPageIndex(database, "items", record, PAGE_SIZE);

		expect(page).toBe(1);
	});

	it("counts every earlier row of a two-column key", () => {
		const database = createDatabase(ASPECTS_SQL);
		const record = { revision: "r2", aspect: "c" };

		const page = rowPageIndex(database, "aspects", record, PAGE_SIZE);

		expect(page).toBe(2);
	});

	it("counts rows with a NULL key before the others", () => {
		const database = createDatabase(`
			CREATE TABLE codes (code TEXT PRIMARY KEY);
			INSERT INTO codes VALUES (NULL), (NULL), ('a'), ('b');
		`);
		const record = { code: "b" };

		const page = rowPageIndex(database, "codes", record, PAGE_SIZE);

		expect(page).toBe(1);
	});

	it("gives the first page for a record with a NULL key value", () => {
		const database = createDatabase(ASPECTS_SQL);
		const record = { revision: null, aspect: "c" };

		const page = rowPageIndex(database, "aspects", record, PAGE_SIZE);

		expect(page).toBe(0);
	});

	it("gives the first page for a table without a primary key", () => {
		const database = createDatabase(`
			CREATE TABLE notes (body TEXT);
			INSERT INTO notes VALUES ('a'), ('b'), ('c'), ('d'), ('e');
		`);
		const record = { body: "e" };

		const page = rowPageIndex(database, "notes", record, PAGE_SIZE);

		expect(page).toBe(0);
	});
});

describe("searchTable", () => {
	it("orders the rows by every key column", () => {
		const database = createDatabase(`${MODL_TABLES_SQL}
			INSERT INTO revision_aspects (revision_uri, aspect_key, operation)
			VALUES ('r2', 'a', 'op'), ('r1', 'b', 'op'), ('r1', 'a', 'op');
		`);

		const result = searchTable(database, "revision_aspects", "");
		const keys = result.rows.map((row) => row.slice(0, 2));

		expect(keys).toEqual([
			["r1", "a"],
			["r1", "b"],
			["r2", "a"],
		]);
	});
});

describe("countSearchMatches", () => {
	it("counts the rows that the same search and filters return", () => {
		const database = createDatabase(`${MODL_TABLES_SQL}
			INSERT INTO concepts (serial, concept_uri, current_label, kind, status)
			VALUES
				(0, 'c0', 'Car', 'ENTITY', 'ACTIVE'),
				(1, 'c1', 'Cart', 'ENTITY', 'REMOVED'),
				(2, 'c2', 'Person', 'ENTITY', 'ACTIVE');
		`);
		const options = { filters: { status: "ACTIVE" } };

		const result = searchTable(database, "concepts", "car", options);
		const count = countSearchMatches(database, "concepts", "car", options);
		const records = toRecords(result);
		const labels = records.map((record) => record.current_label);

		expect(labels).toEqual(["Car"]);
		expect(count).toBe(1);
	});
});
