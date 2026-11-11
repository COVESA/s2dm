import {
	identityColumnsOf,
	singleIdentityColumnFor,
} from "@ledger-ui/data/identity";
import { describe, expect, it } from "vitest";
import { column, foreignKey, ledgerTable } from "./fixtures";

const CONTRACT_COLUMNS = [
	column("serial", 1),
	column("concept_uri"),
	column("contract_uri"),
];
const CONTRACT_KEYS = [foreignKey("concept_uri", "concepts")];
const CONTRACTS = ledgerTable("contracts", CONTRACT_COLUMNS, CONTRACT_KEYS);

const ASPECT_COLUMNS = [
	column("revision_uri", 1),
	column("aspect_key", 2),
	column("operation"),
];
const ASPECT_KEYS = [foreignKey("revision_uri", "revisions")];
const REVISION_ASPECTS = ledgerTable(
	"revision_aspects",
	ASPECT_COLUMNS,
	ASPECT_KEYS,
);

const NOTE_COLUMNS = [column("body"), column("author")];
const NOTES = ledgerTable("notes", NOTE_COLUMNS);

describe("identityColumnsOf", () => {
	it("uses the own URI column and skips foreign key columns", () => {
		const identityColumns = identityColumnsOf(CONTRACTS);

		expect(identityColumns).toEqual(["contract_uri"]);
	});

	it("uses the primary key when every URI column is a foreign key", () => {
		const identityColumns = identityColumnsOf(REVISION_ASPECTS);

		expect(identityColumns).toEqual(["revision_uri", "aspect_key"]);
	});

	it("uses the first column when there is no URI column and no key", () => {
		const identityColumns = identityColumnsOf(NOTES);

		expect(identityColumns).toEqual(["body"]);
	});
});

describe("singleIdentityColumnFor", () => {
	const tables = [CONTRACTS, REVISION_ASPECTS];

	it("gives the column of a one-column identity", () => {
		const identityColumn = singleIdentityColumnFor(tables, "contracts");

		expect(identityColumn).toBe("contract_uri");
	});

	it("gives null for an identity of several columns", () => {
		const identityColumn = singleIdentityColumnFor(tables, "revision_aspects");

		expect(identityColumn).toBeNull();
	});

	it("gives null for a missing table", () => {
		const identityColumn = singleIdentityColumnFor(tables, "bindings");

		expect(identityColumn).toBeNull();
	});
});
