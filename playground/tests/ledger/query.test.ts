import { isReadOnlyStatement, runReadQuery } from "@ledger-ui/data/query";
import { readAll } from "@ledger-ui/data/sql";
import { describe, expect, it } from "vitest";
import { createDatabase } from "./fixtures";

function createItemsDatabase() {
	return createDatabase(`
		CREATE TABLE items (serial INTEGER PRIMARY KEY);
		INSERT INTO items VALUES (1), (2), (3);
	`);
}

describe("isReadOnlyStatement", () => {
	it.each([
		"SELECT * FROM concepts",
		"with recent as (select 1) select * from recent",
		"EXPLAIN QUERY PLAN SELECT 1",
		"-- a note\nSELECT 1",
		"/* a note */ SELECT 1",
	])("accepts %j", (sql) => {
		const isReadOnly = isReadOnlyStatement(sql);

		expect(isReadOnly).toBe(true);
	});

	it.each([
		"DELETE FROM concepts",
		"UPDATE concepts SET kind = 'ENTITY'",
		"-- SELECT\nDELETE FROM concepts",
		"/* SELECT */ DELETE FROM concepts",
	])("rejects %j", (sql) => {
		const isReadOnly = isReadOnlyStatement(sql);

		expect(isReadOnly).toBe(false);
	});
});

describe("runReadQuery", () => {
	it("does not run a write", () => {
		const database = createItemsDatabase();

		expect(() => runReadQuery(database, "DELETE FROM items")).toThrow(Error);
		const { rows } = readAll(database, "SELECT COUNT(*) FROM items");
		expect(rows[0]?.[0]).toBe(3);
	});

	it("marks a result cut at the limit as truncated", () => {
		const database = createItemsDatabase();

		const result = runReadQuery(database, "SELECT * FROM items", { limit: 2 });

		expect(result.rows).toHaveLength(2);
		expect(result.truncated).toBe(true);
	});

	it("does not mark a complete result as truncated", () => {
		const database = createItemsDatabase();

		const result = runReadQuery(database, "SELECT * FROM items", { limit: 3 });

		expect(result.rows).toHaveLength(3);
		expect(result.truncated).toBe(false);
	});
});
