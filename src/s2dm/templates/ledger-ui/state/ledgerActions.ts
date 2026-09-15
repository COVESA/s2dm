import type { SearchOptions } from "@ledger-ui/data/search";
import type {
	LedgerCell,
	LedgerRecord,
	LedgerTable,
} from "@ledger-ui/data/types";
import { createAction } from "@reduxjs/toolkit";

export type LedgerView = "raw" | "explore" | "query" | "schema";

// Actions more than one slice reacts to. Declared here so no slice imports
// another, which would put action creators in an import cycle.
// Bytes rather than a File: one host picks a file, another fetches a ledger it ships.
export const openLedger = createAction<{ name: string; bytes: Uint8Array }>(
	"ledger/openLedger",
);
export const openLedgerSuccess = createAction<{
	fileName: string;
	tables: LedgerTable[];
}>("ledger/openLedgerSuccess");
export const openLedgerFailure = createAction<{
	message: string;
	cleared: boolean;
}>("ledger/openLedgerFailure");
export const closeLedger = createAction("ledger/closeLedger");

export const setLedgerView = createAction<LedgerView>("ledger/setLedgerView");
export const setSearchOptions = createAction<Partial<SearchOptions>>(
	"ledger/setSearchOptions",
);

export const showRecordInTable = createAction<{
	table: string;
	record: LedgerRecord;
}>("ledger/showRecordInTable");
// A row clicked in the query results. Whether it is a record of a table or a
// projection cannot be told from the result alone, so the saga decides.
export const openLedgerQueryRow = createAction<{
	record: LedgerRecord;
	cells: LedgerCell[];
}>("ledger/openLedgerQueryRow");

// Stops a query that is already running. SQLite cannot be interrupted, so the
// saga ends the worker thread rather than asking it to stop.
export const cancelLedgerQuery = createAction("ledger/cancelLedgerQuery");

export const openTableWithSearch = createAction<{
	table: string;
	search: string;
}>("ledger/openTableWithSearch");
