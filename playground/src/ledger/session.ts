import type { Database } from "sql.js";

let database: Database | null = null;

export function setLedgerDatabase(next: Database): void {
	database?.close();
	database = next;
}

export function getLedgerDatabase(): Database {
	if (!database) {
		throw new Error("No ledger database is loaded.");
	}
	return database;
}

export function closeLedgerDatabase(): void {
	database?.close();
	database = null;
}
