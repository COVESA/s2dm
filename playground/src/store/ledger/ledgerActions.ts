import { createAction } from "@reduxjs/toolkit";
import type { SearchOptions } from "@/ledger/search";
import type { LedgerRecord, LedgerTable } from "@/ledger/types";

export type LedgerView = "raw" | "explore" | "query";

// Actions more than one slice reacts to. Declared here so no slice imports
// another, which would put action creators in an import cycle.
export const openLedger = createAction<File>("ledger/openLedger");
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
export const openTableWithSearch = createAction<{
	table: string;
	search: string;
}>("ledger/openTableWithSearch");
