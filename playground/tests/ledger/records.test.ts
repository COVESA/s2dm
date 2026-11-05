import {
	dimensionsOf,
	formatDimension,
	instanceDimensions,
	instanceTagDimensions,
} from "@ledger-ui/data/instances";
import {
	ABSENT_VALUE,
	formatValue,
	recordLabel,
	recordTypeName,
	tableTitle,
} from "@ledger-ui/data/recordLabel";
import {
	findLedgerReferences,
	referenceTableOf,
} from "@ledger-ui/data/references";
import {
	matchResultTable,
	storedRecordTable,
} from "@ledger-ui/data/resultRecord";
import { isRecordOnPage, isSameRow } from "@ledger-ui/data/resultRow";
import { readSchema } from "@ledger-ui/data/schema";
import { describe, expect, it } from "vitest";
import {
	column,
	createDatabase,
	ledgerTable,
	MODL_TABLES_SQL,
} from "./fixtures";

describe("matchResultTable", () => {
	const itemColumns = [column("serial", 1), column("label")];
	const noteColumns = [column("serial", 1), column("body")];
	const items = ledgerTable("items", itemColumns);
	const tags = ledgerTable("tags", itemColumns);
	const notes = ledgerTable("notes", noteColumns);

	it("gives the one table with exactly these columns", () => {
		const table = matchResultTable(["label", "serial"], [items, notes]);

		expect(table).toBe("items");
	});

	it("gives null when no table has exactly these columns", () => {
		const table = matchResultTable(["serial"], [items, notes]);

		expect(table).toBeNull();
	});

	it("gives null when several tables have these columns", () => {
		const table = matchResultTable(["serial", "label"], [items, tags]);

		expect(table).toBeNull();
	});
});

describe("storedRecordTable", () => {
	const database = createDatabase(`
		CREATE TABLE items (serial INTEGER PRIMARY KEY, label TEXT);
		INSERT INTO items VALUES (1, 'a'), (2, 'b');
	`);
	const tables = readSchema(database);
	const columns = ["serial", "label"];

	it("matches a query row to its stored record", () => {
		const record = { serial: 2, label: "b" };

		const table = storedRecordTable(database, columns, record, tables);

		expect(table).toBe("items");
	});

	it("gives null when a value differs from the stored record", () => {
		const record = { serial: 2, label: "changed" };

		const table = storedRecordTable(database, columns, record, tables);

		expect(table).toBeNull();
	});

	it("gives null when the identity value is missing", () => {
		const record = { serial: null, label: "b" };

		const table = storedRecordTable(database, columns, record, tables);

		expect(table).toBeNull();
	});

	it("matches a row of a table keyed by two columns", () => {
		const aspectDatabase = createDatabase(`${MODL_TABLES_SQL}
			INSERT INTO revision_aspects (revision_uri, aspect_key, operation)
			VALUES ('r1', 'a', 'op'), ('r1', 'b', 'op');
		`);
		const aspectTables = readSchema(aspectDatabase);
		const aspectColumns = [
			"revision_uri",
			"aspect_key",
			"operation",
			"previous_value",
			"newer_value",
			"reason",
		];
		const record = {
			revision_uri: "r1",
			aspect_key: "b",
			operation: "op",
			previous_value: null,
			newer_value: null,
			reason: null,
		};

		const table = storedRecordTable(
			aspectDatabase,
			aspectColumns,
			record,
			aspectTables,
		);

		expect(table).toBe("revision_aspects");
	});
});

describe("referenceTableOf", () => {
	const tableNames = ["concepts"];

	it("gives the table that a URI names", () => {
		const table = referenceTableOf("http://ex/concepts/0", tableNames);

		expect(table).toBe("concepts");
	});

	it.each([
		"http://ex/unknown/0",
		"concepts/0",
		'{"http://ex/concepts/0":{"dimension1":"Front"}}',
		42,
	])("gives null for %j", (value) => {
		const table = referenceTableOf(value, tableNames);

		expect(table).toBeNull();
	});
});

describe("findLedgerReferences", () => {
	it("finds each URI once, in table order", () => {
		const tableNames = ["concepts", "contracts", "bindings"];
		const cells = [
			{ column: "binding_uri", value: "http://ex/bindings/0" },
			{ column: "contract_uri", value: "http://ex/contracts/1" },
			{ column: "current_label", value: "Car.id" },
			{ column: "concept_uri", value: "http://ex/concepts/1" },
			{ column: "target_contract_uri", value: "http://ex/contracts/1" },
		];

		const references = findLedgerReferences(cells, tableNames);

		expect(references).toEqual([
			{
				table: "concepts",
				column: "concept_uri",
				value: "http://ex/concepts/1",
			},
			{
				table: "contracts",
				column: "contract_uri",
				value: "http://ex/contracts/1",
			},
			{
				table: "bindings",
				column: "binding_uri",
				value: "http://ex/bindings/0",
			},
		]);
	});
});

describe("isSameRow", () => {
	it("matches rows with the same values", () => {
		const isSame = isSameRow([1, "a", null], [1, "a", null]);

		expect(isSame).toBe(true);
	});

	it("does not match rows of different length", () => {
		const isSame = isSameRow([1, "a"], [1]);

		expect(isSame).toBe(false);
	});

	it("matches binary values by their bytes", () => {
		const first = new Uint8Array([1, 2]);
		const second = new Uint8Array([1, 2]);

		const isSame = isSameRow([first], [second]);

		expect(isSame).toBe(true);
	});

	it("does not match binary values with other bytes", () => {
		const first = new Uint8Array([1, 2]);
		const second = new Uint8Array([1, 3]);

		const isSame = isSameRow([first], [second]);

		expect(isSame).toBe(false);
	});

	it("does not match a binary value with text", () => {
		const bytes = new Uint8Array([1, 2]);

		const isSame = isSameRow([bytes], ["1,2"]);

		expect(isSame).toBe(false);
	});
});

describe("isRecordOnPage", () => {
	const page = {
		columns: ["serial", "label"],
		rows: [
			[1, "a"],
			[2, "b"],
		],
		truncated: false,
	};

	it("is true for a row of the page", () => {
		const onPage = isRecordOnPage(page, { serial: 2, label: "b" });

		expect(onPage).toBe(true);
	});

	it("is false when one value of the record differs", () => {
		const onPage = isRecordOnPage(page, { serial: 2, label: "changed" });

		expect(onPage).toBe(false);
	});
});

describe("instanceDimensions", () => {
	it("reads each dimension with its values, in order", () => {
		const value =
			'{"dimension1": ["Front", "Rear"], "dimension2": ["Left", "Right"]}';

		const dimensions = instanceDimensions(value);

		expect(dimensions).toEqual([
			{ name: "dimension1", values: ["Front", "Rear"] },
			{ name: "dimension2", values: ["Left", "Right"] },
		]);
	});

	it("gives no dimensions for an empty object", () => {
		const dimensions = instanceDimensions("{}");

		expect(dimensions).toEqual([]);
	});

	it.each([
		null,
		"not json",
		"[1]",
		'{"dimension1": [1]}',
		'{"dimension1": "Front"}',
	])("gives null for %j", (value) => {
		const dimensions = instanceDimensions(value);

		expect(dimensions).toBeNull();
	});
});

describe("instanceTagDimensions", () => {
	it("reads each dimension with its instance, without the entity", () => {
		const value =
			'{"http://ex/concepts/a": {"dimension1": "Front", "dimension2": "Right"}}';

		const dimensions = instanceTagDimensions(value);

		expect(dimensions).toEqual([
			{ name: "dimension1", values: ["Front"] },
			{ name: "dimension2", values: ["Right"] },
		]);
	});

	it("reads the tags of every entity, in order", () => {
		const value =
			'{"http://ex/concepts/a": {"dimension1": "Front"}, "http://ex/concepts/b": {"dimension1": "Left"}}';

		const dimensions = instanceTagDimensions(value);

		expect(dimensions).toEqual([
			{ name: "dimension1", values: ["Front"] },
			{ name: "dimension1", values: ["Left"] },
		]);
	});

	it("gives no dimensions for a singleton", () => {
		const dimensions = instanceTagDimensions("{}");

		expect(dimensions).toEqual([]);
	});

	it.each([
		null,
		"not json",
		'{"http://ex/concepts/a": ["Front"]}',
		'{"http://ex/concepts/a": {"dimension1": 1}}',
	])("gives null for %j", (value) => {
		const dimensions = instanceTagDimensions(value);

		expect(dimensions).toBeNull();
	});
});

describe("dimensionsOf", () => {
	it("reads a value with the shape of instance tags", () => {
		const tags = '{"http://ex/concepts/a": {"dimension1": "Front"}}';

		const dimensions = dimensionsOf(tags);

		expect(dimensions).toEqual([{ name: "dimension1", values: ["Front"] }]);
	});

	it("reads a value with the shape of instances", () => {
		const instances = '{"dimension1": ["Front", "Rear"]}';

		const dimensions = dimensionsOf(instances);

		expect(dimensions).toEqual([
			{ name: "dimension1", values: ["Front", "Rear"] },
		]);
	});

	it("gives no dimensions for an empty object", () => {
		const dimensions = dimensionsOf("{}");

		expect(dimensions).toEqual([]);
	});

	it.each(['["Front"]', "Front"])("gives null for %j", (value) => {
		const dimensions = dimensionsOf(value);

		expect(dimensions).toBeNull();
	});
});

describe("formatDimension", () => {
	it("writes the dimension name and its values", () => {
		const dimension = { name: "dimension1", values: ["Front", "Rear"] };

		const text = formatDimension(dimension);

		expect(text).toBe("dimension1: Front, Rear");
	});
});

describe("formatValue", () => {
	it("shows the absent value for null", () => {
		const text = formatValue(null);

		expect(text).toBe(ABSENT_VALUE);
	});

	it("shows the size of a binary value", () => {
		const bytes = new Uint8Array([1, 2, 3]);

		const text = formatValue(bytes);

		expect(text).toBe("3 bytes");
	});

	it("shows a number as text", () => {
		const text = formatValue(5);

		expect(text).toBe("5");
	});
});

describe("recordLabel", () => {
	it("uses the first label column that has a value", () => {
		const record = { current_label: "", runtime_path: "Car.id", role: "unit" };

		const label = recordLabel(record);

		expect(label).toBe("Car.id");
	});

	it("is empty when no label column has a value", () => {
		const label = recordLabel({ serial: 1 });

		expect(label).toBe("");
	});
});

describe("tableTitle", () => {
	it("writes underscores as spaces and capitalises the first letter", () => {
		const title = tableTitle("revision_aspects");

		expect(title).toBe("Revision aspects");
	});
});

describe("recordTypeName", () => {
	it("writes a table name as the type of one record", () => {
		const typeName = recordTypeName("revision_aspects");

		expect(typeName).toBe("Revision aspect");
	});
});
