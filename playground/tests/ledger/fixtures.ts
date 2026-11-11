import type {
	LedgerColumn,
	LedgerForeignKey,
	LedgerTable,
} from "@ledger-ui/data/types";
import initSqlJs, { type Database } from "sql.js";

const sqlJs = await initSqlJs();

// The tables as `modl export sqlite` writes them.
export const MODL_TABLES_SQL = `
CREATE TABLE "concepts" (
    "serial" INTEGER NOT NULL PRIMARY KEY,
    "concept_uri" TEXT NOT NULL UNIQUE,
    "current_label" TEXT NOT NULL,
    "previous_labels" TEXT,
    "kind" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "parent_uri" TEXT,
    "instances" TEXT,
    FOREIGN KEY ("parent_uri") REFERENCES "concepts" ("concept_uri")
);
CREATE TABLE "revisions" (
    "serial" INTEGER NOT NULL PRIMARY KEY,
    "revision_uri" TEXT NOT NULL UNIQUE,
    "concept_uri" TEXT NOT NULL,
    "previous_revision_uri" TEXT,
    "status" TEXT NOT NULL,
    FOREIGN KEY ("concept_uri") REFERENCES "concepts" ("concept_uri"),
    FOREIGN KEY ("previous_revision_uri") REFERENCES "revisions" ("revision_uri")
);
CREATE TABLE "contracts" (
    "serial" INTEGER NOT NULL PRIMARY KEY,
    "contract_uri" TEXT NOT NULL UNIQUE,
    "concept_uri" TEXT NOT NULL,
    "revision_uri" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    FOREIGN KEY ("concept_uri") REFERENCES "concepts" ("concept_uri"),
    FOREIGN KEY ("revision_uri") REFERENCES "revisions" ("revision_uri")
);
CREATE TABLE "bindings" (
    "serial" INTEGER NOT NULL PRIMARY KEY,
    "binding_uri" TEXT NOT NULL UNIQUE,
    "contract_uri" TEXT NOT NULL,
    "instance_tags" TEXT NOT NULL,
    "runtime_path" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    FOREIGN KEY ("contract_uri") REFERENCES "contracts" ("contract_uri")
);
CREATE TABLE "revision_aspects" (
    "revision_uri" TEXT NOT NULL,
    "aspect_key" TEXT NOT NULL,
    "operation" TEXT NOT NULL,
    "previous_value" TEXT,
    "newer_value" TEXT,
    "reason" TEXT,
    PRIMARY KEY ("revision_uri", "aspect_key"),
    FOREIGN KEY ("revision_uri") REFERENCES "revisions" ("revision_uri")
);
CREATE TABLE "contract_references" (
    "contract_uri" TEXT NOT NULL,
    "role" TEXT NOT NULL,
    "target_contract_uri" TEXT NOT NULL,
    PRIMARY KEY ("contract_uri", "role"),
    FOREIGN KEY ("contract_uri") REFERENCES "contracts" ("contract_uri"),
    FOREIGN KEY ("target_contract_uri") REFERENCES "contracts" ("contract_uri")
);
`;

export function createDatabase(sql: string): Database {
	const database = new sqlJs.Database();
	database.exec(sql);
	return database;
}

export function column(name: string, primaryKeyPosition = 0): LedgerColumn {
	return { name, declaredType: "TEXT", notNull: false, primaryKeyPosition };
}

export function foreignKey(
	columnName: string,
	referencesTable: string,
	referencesColumn: string = columnName,
): LedgerForeignKey {
	return { column: columnName, referencesTable, referencesColumn };
}

export function ledgerTable(
	name: string,
	columns: LedgerColumn[],
	foreignKeys: LedgerForeignKey[] = [],
): LedgerTable {
	return { name, columns, foreignKeys, rowCount: 0, activeCount: null };
}
