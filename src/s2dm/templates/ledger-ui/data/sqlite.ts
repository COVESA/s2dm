import { registerSearchFunction } from "@ledger-ui/data/search";
import type { Database, SqlJsStatic } from "sql.js";

let sqlJs: Promise<SqlJsStatic> | null = null;
let wasmUrl: string | null = null;

// Host-provided because each bundler names the asset its own way. Call once
// before the first ledger opens.
export function configureSqlJs(options: { wasmUrl: string }): void {
	wasmUrl = options.wasmUrl;
}

function loadSqlJs(): Promise<SqlJsStatic> {
	const configuredUrl = wasmUrl;
	if (!configuredUrl) {
		throw new Error("configureSqlJs has not been called with a wasm URL.");
	}
	// Caches into module state so the wasm loads once. On demand to keep it out
	// of the initial bundle; a failure is not cached, so a retry can succeed.
	sqlJs ??= import("sql.js")
		.then((module) => module.default({ locateFile: () => configuredUrl }))
		.catch((error) => {
			sqlJs = null;
			throw error;
		});
	return sqlJs;
}

export async function openLedgerDatabase(bytes: Uint8Array): Promise<Database> {
	const { Database: SqlDatabase } = await loadSqlJs();
	const database = new SqlDatabase(bytes);
	// Enforced by SQLite: `WITH … DELETE … RETURNING` passes both string checks.
	database.run("PRAGMA query_only = 1");
	// SQLite has no regex of its own, so whole-word and regex search need one.
	registerSearchFunction(database);
	return database;
}

export async function readFileBytes(file: File): Promise<Uint8Array> {
	return new Uint8Array(await file.arrayBuffer());
}
