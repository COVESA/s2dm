import type { Database, SqlJsStatic } from "sql.js";
import wasmUrl from "sql.js/dist/sql-wasm-browser.wasm?url";

let sqlJs: Promise<SqlJsStatic> | null = null;

function loadSqlJs(): Promise<SqlJsStatic> {
	// On demand to keep the wasm out of the initial bundle; a failure is not cached.
	sqlJs ??= import("sql.js")
		.then((module) => module.default({ locateFile: () => wasmUrl }))
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
	return database;
}

export async function readFileBytes(file: File): Promise<Uint8Array> {
	return new Uint8Array(await file.arrayBuffer());
}
