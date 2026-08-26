import type { Database } from "sql.js";

let database: Database | null = null;
// Cancellation stops the saga at its yield, and its finally runs before the
// open resolves, so a superseded import has to close its own database.
let generation = 0;

export function beginLedgerOpen(): number {
	generation += 1;
	return generation;
}

export function isCurrentLedgerOpen(token: number): boolean {
	return token === generation;
}

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
	// Also retires any import still in flight, which would otherwise install
	// itself over a ledger the user has just removed.
	generation += 1;
	database?.close();
	database = null;
}
