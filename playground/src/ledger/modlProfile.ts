import type { LedgerTable } from "@/ledger/types";

// The ModL model as data, mirroring EXPECTED_COLUMNS and FK_CONSTRAINTS in
// modl/ledger.py. ModL emits CSV, so whatever converts it to SQLite may declare
// no keys at all, and every structural feature here reads them.
export const MODL_TABLES: Record<
	string,
	{ primaryKey: string; columns: string[] }
> = {
	concepts: {
		primaryKey: "serial",
		columns: [
			"serial",
			"concept_uri",
			"current_label",
			"previous_labels",
			"kind",
			"status",
			"parent_uri",
			"instances",
		],
	},
	revisions: {
		primaryKey: "serial",
		columns: [
			"serial",
			"revision_uri",
			"concept_uri",
			"previous_revision_uri",
			"status",
		],
	},
	contracts: {
		primaryKey: "serial",
		columns: [
			"serial",
			"contract_uri",
			"concept_uri",
			"revision_uri",
			"status",
		],
	},
	bindings: {
		primaryKey: "serial",
		columns: [
			"serial",
			"binding_uri",
			"contract_uri",
			"instance_label",
			"status",
		],
	},
};

export const MODL_STATUSES = ["ACTIVE", "SUPERSEDED", "REMOVED"] as const;
export type ModlStatus = (typeof MODL_STATUSES)[number];

export const STATUS_COLUMN = "status";
export const KIND_COLUMN = "kind";
export const ACTIVE_STATUS: ModlStatus = "ACTIVE";

export const FILTERABLE_COLUMNS = [KIND_COLUMN, STATUS_COLUMN] as const;

export const LABEL_COLUMNS = ["current_label", "instance_label"] as const;

export type ModlRelationship = {
	table: string;
	column: string;
	referencesTable: string;
	referencesColumn: string;
	label?: string;
};

export const MODL_FOREIGN_KEYS: ModlRelationship[] = [
	{
		table: "concepts",
		column: "parent_uri",
		referencesTable: "concepts",
		referencesColumn: "concept_uri",
		label: "parent of",
	},
	{
		table: "revisions",
		column: "concept_uri",
		referencesTable: "concepts",
		referencesColumn: "concept_uri",
		label: "tracked by",
	},
	{
		table: "revisions",
		column: "previous_revision_uri",
		referencesTable: "revisions",
		referencesColumn: "revision_uri",
		label: "supersedes",
	},
	{
		table: "contracts",
		column: "concept_uri",
		referencesTable: "concepts",
		referencesColumn: "concept_uri",
		label: "realized as",
	},
	{
		table: "contracts",
		column: "revision_uri",
		referencesTable: "revisions",
		referencesColumn: "revision_uri",
		label: "triggers",
	},
	{
		table: "bindings",
		column: "contract_uri",
		referencesTable: "contracts",
		referencesColumn: "contract_uri",
		label: "expanded into",
	},
];

export type ModlTable = keyof typeof MODL_TABLES;

// Fills in keys and a primary key only where the file declared none, and only
// for columns it actually has: an explicit schema always wins, and a table that
// merely shares a ModL name never gains a key to a column it lacks.
export function applyModlProfile(tables: LedgerTable[]): LedgerTable[] {
	const columnsOf = new Map(
		tables.map((table) => [
			table.name,
			new Set(table.columns.map((column) => column.name)),
		]),
	);

	return tables.map((table) => {
		const profile = MODL_TABLES[table.name];
		if (!profile) {
			return table;
		}

		const own = columnsOf.get(table.name) ?? new Set<string>();
		const hasPrimaryKey = table.columns.some((column) => column.primaryKey);
		const columns =
			hasPrimaryKey || !own.has(profile.primaryKey)
				? table.columns
				: table.columns.map((column) =>
						column.name === profile.primaryKey
							? { ...column, primaryKey: true }
							: column,
					);

		const foreignKeys =
			table.foreignKeys.length > 0
				? table.foreignKeys
				: MODL_FOREIGN_KEYS.filter(
						(key) =>
							key.table === table.name &&
							own.has(key.column) &&
							columnsOf.get(key.referencesTable)?.has(key.referencesColumn),
					).map(({ column, referencesTable, referencesColumn }) => ({
						column,
						referencesTable,
						referencesColumn,
					}));

		return { ...table, columns, foreignKeys };
	});
}
