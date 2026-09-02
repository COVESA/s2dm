import type { Database, SqlJsStatic } from "sql.js";
import wasmUrl from "sql.js/dist/sql-wasm-browser.wasm?url";
import { registerSearchFunction } from "@/ledger/search";
import { isCurrentLedgerOpen } from "@/ledger/session";

let sqlJs: Promise<SqlJsStatic> | null = null;

function loadSqlJs(): Promise<SqlJsStatic> {
	// Caches into module state so the wasm loads once. On demand to keep it out
	// of the initial bundle; a failure is not cached, so a retry can succeed.
	sqlJs ??= import("sql.js")
		.then((module) => module.default({ locateFile: () => wasmUrl }))
		.catch((error) => {
			sqlJs = null;
			throw error;
		});
	return sqlJs;
}

export class LedgerImportSuperseded extends Error {
	constructor() {
		super("Ledger import superseded");
		this.name = "LedgerImportSuperseded";
	}
}

export async function openLedgerDatabase(
	bytes: Uint8Array,
	token: number,
): Promise<Database> {
	const { Database: SqlDatabase } = await loadSqlJs();
	const database = new SqlDatabase(bytes);
	if (!isCurrentLedgerOpen(token)) {
		// Superseded while the wasm loaded: no one will ever receive this.
		database.close();
		throw new LedgerImportSuperseded();
	}
	// Enforced by SQLite: `WITH … DELETE … RETURNING` passes both string checks.
	database.run("PRAGMA query_only = 1");
	// SQLite has no regex of its own, so whole-word and regex search need one.
	registerSearchFunction(database);
	return database;
}

export async function readFileBytes(file: File): Promise<Uint8Array> {
	return new Uint8Array(await file.arrayBuffer());
}
