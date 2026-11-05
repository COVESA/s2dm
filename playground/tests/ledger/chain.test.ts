import { findOne, resolveChain } from "@ledger-ui/data/chainResolve";
import {
	chainNodeKey,
	deriveChainSpec,
	identityOf,
	levelOf,
	selectedAncestry,
} from "@ledger-ui/data/chainSpec";
import { readSchema } from "@ledger-ui/data/schema";
import { describe, expect, it } from "vitest";
import {
	column,
	createDatabase,
	foreignKey,
	ledgerTable,
	MODL_TABLES_SQL,
} from "./fixtures";

const CAR_ID_LEDGER_SQL = `
INSERT INTO concepts (serial, concept_uri, current_label, kind, status, parent_uri) VALUES
    (0, 'http://ex/concepts/0', 'Car', 'ENTITY', 'ACTIVE', NULL),
    (1, 'http://ex/concepts/1', 'Car.id', 'PROPERTY', 'ACTIVE', 'http://ex/concepts/0');
INSERT INTO revisions (serial, revision_uri, concept_uri, status) VALUES
    (0, 'http://ex/revisions/0', 'http://ex/concepts/0', 'ACTIVE'),
    (1, 'http://ex/revisions/1', 'http://ex/concepts/1', 'ACTIVE');
INSERT INTO contracts (serial, contract_uri, concept_uri, revision_uri, status) VALUES
    (0, 'http://ex/contracts/0', 'http://ex/concepts/0', 'http://ex/revisions/0', 'ACTIVE'),
    (1, 'http://ex/contracts/1', 'http://ex/concepts/1', 'http://ex/revisions/1', 'ACTIVE');
INSERT INTO bindings (serial, binding_uri, contract_uri, instance_tags, runtime_path, status) VALUES
    (0, 'http://ex/bindings/0', 'http://ex/contracts/1', '{}', 'Car.id', 'ACTIVE');
`;

const MANY_REVISIONS_SQL = `
INSERT INTO concepts (serial, concept_uri, current_label, kind, status) VALUES
    (0, 'http://ex/concepts/0', 'Car', 'ENTITY', 'ACTIVE');
WITH RECURSIVE counter (n) AS (
    SELECT 0
    UNION ALL
    SELECT n + 1 FROM counter WHERE n < 104
)
INSERT INTO revisions (serial, revision_uri, concept_uri, status)
SELECT n, 'http://ex/revisions/' || n, 'http://ex/concepts/0', 'ACTIVE' FROM counter;
`;

describe("identityOf", () => {
	const keyColumns = ["revision_uri", "aspect_key"];

	it("keeps values apart when a value contains a separator", () => {
		const first = identityOf(
			{ revision_uri: "http://ex/revisions/0 · a", aspect_key: "b" },
			keyColumns,
		);
		const second = identityOf(
			{ revision_uri: "http://ex/revisions/0", aspect_key: "a · b" },
			keyColumns,
		);

		expect(first).not.toBe(second);
	});

	it("gives an empty identity when every value is empty", () => {
		const identity = identityOf(
			{ revision_uri: null, aspect_key: "" },
			keyColumns,
		);

		expect(identity).toBe("");
	});
});

describe("deriveChainSpec", () => {
	const database = createDatabase(MODL_TABLES_SQL);
	const tables = readSchema(database);
	const spec = deriveChainSpec(tables);

	it("gives the top table no parent", () => {
		const level = levelOf(spec, "concepts");

		expect(level?.parent).toBeNull();
	});

	it("links a table to the closest earlier parent", () => {
		const level = levelOf(spec, "contracts");

		expect(level?.parent?.table).toBe("revisions");
	});

	it("prefers the key named after the column it references", () => {
		const level = levelOf(spec, "contract_references");

		expect(level?.parent).toEqual({
			table: "contracts",
			column: "contract_uri",
			identityColumn: "contract_uri",
		});
	});

	it("skips a key that targets rowid", () => {
		const pairColumns = [column("first", 1), column("second", 2)];
		const linkColumns = [column("pair")];
		const rowidKey = foreignKey("pair", "pairs", "rowid");
		const rowidTables = [
			ledgerTable("pairs", pairColumns),
			ledgerTable("links", linkColumns, [rowidKey]),
		];

		const rowidSpec = deriveChainSpec(rowidTables);
		const level = levelOf(rowidSpec, "links");

		expect(level?.parent).toBeNull();
	});
});

describe("resolveChain", () => {
	it("walks up from the selected record to the top ancestor", () => {
		const database = createDatabase(`${MODL_TABLES_SQL}${CAR_ID_LEDGER_SQL}`);
		const tables = readSchema(database);
		const binding = findOne(
			database,
			"bindings",
			"binding_uri",
			"http://ex/bindings/0",
		);

		const chain = resolveChain(database, tables, "bindings", binding ?? {});

		expect(chain.root?.table).toBe("concepts");
		expect(chain.root?.identity).toBe('["http://ex/concepts/1"]');
	});

	it("marks every node on the path to the selected record", () => {
		const database = createDatabase(`${MODL_TABLES_SQL}${CAR_ID_LEDGER_SQL}`);
		const tables = readSchema(database);
		const binding = findOne(
			database,
			"bindings",
			"binding_uri",
			"http://ex/bindings/0",
		);
		const path = [
			{ table: "concepts", identity: '["http://ex/concepts/1"]' },
			{ table: "revisions", identity: '["http://ex/revisions/1"]' },
			{ table: "contracts", identity: '["http://ex/contracts/1"]' },
			{ table: "bindings", identity: '["http://ex/bindings/0"]' },
		];
		const expectedKeys = path.map((node) => chainNodeKey(node));
		const expectedAncestry = new Set(expectedKeys);

		const chain = resolveChain(database, tables, "bindings", binding ?? {});
		const ancestry = selectedAncestry(chain.root, chain.selected);

		expect(ancestry).toEqual(expectedAncestry);
	});

	it("keeps the selected record in a group past the fetch limit", () => {
		const database = createDatabase(`${MODL_TABLES_SQL}${MANY_REVISIONS_SQL}`);
		const tables = readSchema(database);
		const revision = findOne(
			database,
			"revisions",
			"revision_uri",
			"http://ex/revisions/104",
		);

		const chain = resolveChain(database, tables, "revisions", revision ?? {});
		const group = chain.root?.groups.find(
			(candidate) => candidate.table === "revisions",
		);
		const identities = group?.nodes.map((node) => node.identity) ?? [];

		expect(group?.total).toBe(105);
		expect(identities).toHaveLength(101);
		expect(identities).toContain('["http://ex/revisions/104"]');
	});

	it("gives no root for a table outside the chain", () => {
		const database = createDatabase(MODL_TABLES_SQL);
		const tables = readSchema(database);

		const chain = resolveChain(database, tables, "notes", {});

		expect(chain.root).toBeNull();
		expect(chain.selected).toEqual({ table: "notes", identity: "" });
	});
});
