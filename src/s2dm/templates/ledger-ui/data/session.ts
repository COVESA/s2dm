import type { Database } from "sql.js";

let database: Database | null = null;
// A cancelled takeLatest task never resumes past its yield, so nothing after
// openLedgerDatabase runs and the database it opened has to close itself.
let generation = 0;

// Call before opening: the token it returns identifies this import attempt.
export function beginLedgerOpen(): number {
	generation += 1;
	return generation;
}

// False once a newer import has begun or the ledger has been removed, which is
// the only signal a superseded open gets.
export function isCurrentLedgerOpen(token: number): boolean {
	return token === generation;
}

// Takes ownership, closing whatever it replaces. Never call it for a database
// that isCurrentLedgerOpen has already rejected.
export function setLedgerDatabase(next: Database): void {
	database?.close();
	database = next;
}

// Throws rather than returning null: every caller runs after a successful open,
// so an absent database is a bug and not a state to branch on.
export function getLedgerDatabase(): Database {
	if (!database) {
		throw new Error("No ledger database is loaded.");
	}
	return database;
}

// Leaves no database loaded, and no import able to load one.
export function closeLedgerDatabase(): void {
	// Also retires any import still in flight, which would otherwise install
	// itself over a ledger the user has just removed.
	generation += 1;
	database?.close();
	database = null;
}
