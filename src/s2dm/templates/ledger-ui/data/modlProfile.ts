import type { LedgerForeignKey } from "@ledger-ui/data/types";

export const MODL_STATUSES = ["ACTIVE", "SUPERSEDED", "REMOVED"] as const;
export type ModlStatus = (typeof MODL_STATUSES)[number];

export const STATUS_COLUMN = "status";
export const KIND_COLUMN = "kind";
export const ACTIVE_STATUS: ModlStatus = "ACTIVE";

export const FILTERABLE_COLUMNS = [KIND_COLUMN, STATUS_COLUMN] as const;

export const LABEL_COLUMNS = [
	"current_label",
	"runtime_path",
	"aspect_key",
	"role",
] as const;

export type ModlTableSchema = {
	name: string;
	columns: string[];
	primaryKey: string[];
	foreignKeys: LedgerForeignKey[];
};

// The tables, columns and keys that `modl export sqlite` writes, from
// EXPECTED_COLUMNS, UNIQUE_COLUMNS, COMPOSITE_KEY_COLUMNS and FK_CONSTRAINTS in
// modl/ledger.py.
export const MODL_SCHEMA: ModlTableSchema[] = [
	{
		name: "concepts",
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
		primaryKey: ["serial"],
		foreignKeys: [
			{
				column: "parent_uri",
				referencesTable: "concepts",
				referencesColumn: "concept_uri",
			},
		],
	},
	{
		name: "revisions",
		columns: [
			"serial",
			"revision_uri",
			"concept_uri",
			"previous_revision_uri",
			"status",
		],
		primaryKey: ["serial"],
		foreignKeys: [
			{
				column: "concept_uri",
				referencesTable: "concepts",
				referencesColumn: "concept_uri",
			},
			{
				column: "previous_revision_uri",
				referencesTable: "revisions",
				referencesColumn: "revision_uri",
			},
		],
	},
	{
		name: "contracts",
		columns: [
			"serial",
			"contract_uri",
			"concept_uri",
			"revision_uri",
			"status",
		],
		primaryKey: ["serial"],
		foreignKeys: [
			{
				column: "concept_uri",
				referencesTable: "concepts",
				referencesColumn: "concept_uri",
			},
			{
				column: "revision_uri",
				referencesTable: "revisions",
				referencesColumn: "revision_uri",
			},
		],
	},
	{
		name: "bindings",
		columns: [
			"serial",
			"binding_uri",
			"contract_uri",
			"instance_tags",
			"runtime_path",
			"status",
		],
		primaryKey: ["serial"],
		foreignKeys: [
			{
				column: "contract_uri",
				referencesTable: "contracts",
				referencesColumn: "contract_uri",
			},
		],
	},
	{
		name: "revision_aspects",
		columns: [
			"revision_uri",
			"aspect_key",
			"operation",
			"previous_value",
			"newer_value",
			"reason",
		],
		primaryKey: ["revision_uri", "aspect_key"],
		foreignKeys: [
			{
				column: "revision_uri",
				referencesTable: "revisions",
				referencesColumn: "revision_uri",
			},
		],
	},
	{
		name: "contract_references",
		columns: ["contract_uri", "role", "target_contract_uri"],
		primaryKey: ["contract_uri", "role"],
		foreignKeys: [
			{
				column: "contract_uri",
				referencesTable: "contracts",
				referencesColumn: "contract_uri",
			},
			{
				column: "target_contract_uri",
				referencesTable: "contracts",
				referencesColumn: "contract_uri",
			},
		],
	},
];
