import { createSlice, isAnyOf } from "@reduxjs/toolkit";
import { DEFAULT_SEARCH_OPTIONS, type SearchOptions } from "@/ledger/search";
import type { LedgerTable } from "@/ledger/types";
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
} from "@/store/ledger/ledgerActions";
import type { RootState } from "@/store/types";

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

export const selectLedgerFileName = (state: RootState) =>
	state.ledgerFile.fileName;
export const selectLedgerTables = (state: RootState) => state.ledgerFile.tables;
export const selectIsLoadingLedger = (state: RootState) =>
	state.ledgerFile.isLoading;
export const selectLedgerError = (state: RootState) => state.ledgerFile.error;
export const selectHasLedger = (state: RootState) =>
	state.ledgerFile.tables.length > 0;
export const selectLedgerView = (state: RootState) => state.ledgerFile.view;
export const selectSearchOptions = (state: RootState) =>
	state.ledgerFile.searchOptions;
