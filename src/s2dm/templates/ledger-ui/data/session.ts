import type { Database } from "sql.js";

// Worker-thread state: the page never holds a database.
let database: Database | null = null;

export function setLedgerDatabase(next: Database): void {
	database?.close();
	database = next;
}

// Throws rather than returning null: an absent database here is a bug.
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
