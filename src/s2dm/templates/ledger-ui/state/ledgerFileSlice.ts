import {
	DEFAULT_SEARCH_OPTIONS,
	type SearchOptions,
} from "@ledger-ui/data/search";
import type { LedgerTable } from "@ledger-ui/data/types";
import {
	closeLedger,
	type LedgerView,
	openLedger,
	openLedgerFailure,
	openLedgerSuccess,
	openTableWithSearch,
	setLedgerView,
	setSearchOptions,
	showRecordInTable,
} from "@ledger-ui/state/ledgerActions";
import type { LedgerRootState } from "@ledger-ui/state/types";
import { createSlice, isAnyOf } from "@reduxjs/toolkit";

export interface LedgerFileState {
	fileName: string;
	tables: LedgerTable[];
	isLoading: boolean;
	error: string | null;
	// How the ledger is being looked at, which outlives any one view's state.
	view: LedgerView;
	searchOptions: SearchOptions;
}

const initialState: LedgerFileState = {
	fileName: "",
	tables: [],
	isLoading: false,
	error: null,
	view: "raw",
	searchOptions: DEFAULT_SEARCH_OPTIONS,
};

const ledgerFileSlice = createSlice({
	name: "ledgerFile",
	initialState,
	reducers: {},
	extraReducers: (builder) => {
		builder
			.addCase(openLedger, (state) => {
				state.isLoading = true;
				state.error = null;
			})
			.addCase(openLedgerSuccess, (state, action) => {
				state.isLoading = false;
				state.error = null;
				state.fileName = action.payload.fileName;
				state.tables = action.payload.tables;
			})
			.addCase(openLedgerFailure, (state, action) => {
				state.isLoading = false;
				state.error = action.payload.message;
				// Only when this import had already replaced the loaded ledger: a
				// file that never opened must leave the one on screen alone.
				if (action.payload.cleared) {
					state.fileName = "";
					state.tables = [];
				}
			})
			.addCase(closeLedger, (state) => {
				state.isLoading = false;
				state.error = null;
				state.fileName = "";
				state.tables = [];
			})
			.addCase(setLedgerView, (state, action) => {
				state.view = action.payload;
			})
			.addCase(setSearchOptions, (state, action) => {
				state.searchOptions = { ...state.searchOptions, ...action.payload };
			})
			// Both open the raw table view; the table slice handles its own fields.
			.addMatcher(isAnyOf(showRecordInTable, openTableWithSearch), (state) => {
				state.view = "raw";
			});
	},
});

export default ledgerFileSlice.reducer;

export const selectLedgerFileName = (state: LedgerRootState) =>
	state.ledgerFile.fileName;
export const selectLedgerTables = (state: LedgerRootState) =>
	state.ledgerFile.tables;
export const selectIsLoadingLedger = (state: LedgerRootState) =>
	state.ledgerFile.isLoading;
export const selectLedgerError = (state: LedgerRootState) =>
	state.ledgerFile.error;
export const selectHasLedger = (state: LedgerRootState) =>
	state.ledgerFile.tables.length > 0;
export const selectLedgerView = (state: LedgerRootState) =>
	state.ledgerFile.view;
export const selectSearchOptions = (state: LedgerRootState) =>
	state.ledgerFile.searchOptions;
