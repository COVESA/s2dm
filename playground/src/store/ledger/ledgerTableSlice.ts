import { createSlice, isAnyOf, type PayloadAction } from "@reduxjs/toolkit";
import type { QueryResult } from "@/ledger/types";
import {
	closeLedger,
	openLedgerFailure,
	openLedgerSuccess,
	openTableWithSearch,
	setSearchOptions,
	showRecordInTable,
} from "@/store/ledger/ledgerActions";
import type { RootState } from "@/store/types";

export interface LedgerTableState {
	selectedTable: string;
	search: string;
	rows: QueryResult | null;
	rowsTotal: number;
	page: number;
	filters: Record<string, string>;
	filterOptions: Record<string, string[]>;
	isLoadingRows: boolean;
	rowsError: string | null;
}

const initialState: LedgerTableState = {
	selectedTable: "",
	search: "",
	rows: null,
	rowsTotal: 0,
	page: 0,
	filters: {},
	filterOptions: {},
	isLoadingRows: false,
	rowsError: null,
};

// Mutates the draft it is given, as reducers do.
function resetTableView(state: LedgerTableState) {
	Object.assign(state, initialState);
}

const ledgerTableSlice = createSlice({
	name: "ledgerTable",
	initialState,
	reducers: {
		chooseLedgerTable: (state, action: PayloadAction<string>) => {
			resetTableView(state);
			state.selectedTable = action.payload;
			state.isLoadingRows = true;
		},
		setLedgerSearch: (state, action: PayloadAction<string>) => {
			state.search = action.payload;
			state.page = 0;
			state.isLoadingRows = true;
		},
		setLedgerPage: (state, action: PayloadAction<number>) => {
			state.page = Math.max(0, action.payload);
			state.isLoadingRows = true;
		},
		setLedgerFilter: (
			state,
			action: PayloadAction<{ column: string; value: string }>,
		) => {
			if (action.payload.value === "") {
				delete state.filters[action.payload.column];
			} else {
				state.filters[action.payload.column] = action.payload.value;
			}
			state.page = 0;
			state.isLoadingRows = true;
		},
		setLedgerFilterOptions: (
			state,
			action: PayloadAction<Record<string, string[]>>,
		) => {
			state.filterOptions = action.payload;
		},
		loadLedgerRows: (state) => {
			state.isLoadingRows = true;
			state.rowsError = null;
		},
		loadLedgerRowsSuccess: (
			state,
			action: PayloadAction<{ result: QueryResult; total: number }>,
		) => {
			state.isLoadingRows = false;
			state.rowsError = null;
			state.rows = action.payload.result;
			state.rowsTotal = action.payload.total;
		},
		loadLedgerRowsFailure: (state, action: PayloadAction<string>) => {
			state.isLoadingRows = false;
			state.rowsError = action.payload;
		},
	},
	extraReducers: (builder) => {
		builder
			.addCase(openLedgerSuccess, (state, action) => {
				resetTableView(state);
				state.selectedTable = action.payload.tables[0]?.name ?? "";
			})
			.addCase(setSearchOptions, (state) => {
				// Which rows match only changes while a raw search is active, so an
				// unsearched table keeps the page it was on.
				if (state.search.trim() !== "") {
					state.page = 0;
				}
				state.isLoadingRows = true;
			})
			.addCase(showRecordInTable, (state, action) => {
				// The page is left to the saga, which works out where the record is.
				const { page } = state;
				resetTableView(state);
				state.page = page;
				state.selectedTable = action.payload.table;
				state.isLoadingRows = true;
			})
			.addCase(openTableWithSearch, (state, action) => {
				resetTableView(state);
				state.selectedTable = action.payload.table;
				state.isLoadingRows = true;
				state.search = action.payload.search;
			})
			.addMatcher(isAnyOf(closeLedger, openLedgerFailure), (state, action) => {
				if (closeLedger.match(action) || action.payload.cleared) {
					resetTableView(state);
				}
			});
	},
});

export const {
	chooseLedgerTable,
	setLedgerSearch,
	setLedgerPage,
	setLedgerFilter,
	setLedgerFilterOptions,
	loadLedgerRows,
	loadLedgerRowsSuccess,
	loadLedgerRowsFailure,
} = ledgerTableSlice.actions;

export default ledgerTableSlice.reducer;

export const selectSelectedLedgerTable = (state: RootState) =>
	state.ledgerTable.selectedTable;
export const selectLedgerSearch = (state: RootState) =>
	state.ledgerTable.search;
export const selectLedgerRows = (state: RootState) => state.ledgerTable.rows;
export const selectIsLoadingLedgerRows = (state: RootState) =>
	state.ledgerTable.isLoadingRows;
export const selectLedgerRowsError = (state: RootState) =>
	state.ledgerTable.rowsError;
export const selectLedgerRowsTotal = (state: RootState) =>
	state.ledgerTable.rowsTotal;
export const selectLedgerPage = (state: RootState) => state.ledgerTable.page;
export const selectLedgerFilters = (state: RootState) =>
	state.ledgerTable.filters;
export const selectLedgerFilterOptions = (state: RootState) =>
	state.ledgerTable.filterOptions;
