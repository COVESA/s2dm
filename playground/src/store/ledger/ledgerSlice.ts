import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import type { LedgerChain } from "@/ledger/chain";
import type {
	LedgerRecord,
	LedgerSearchMatch,
	LedgerTable,
	QueryResult,
} from "@/ledger/types";
import type { RootState } from "@/store/types";

export type LedgerView = "raw" | "explore" | "query";

export interface LedgerState {
	fileName: string;
	tables: LedgerTable[];
	isLoading: boolean;
	error: string | null;
	view: LedgerView;
	selectedTable: string;
	search: string;
	rows: QueryResult | null;
	rowsTotal: number;
	page: number;
	filters: Record<string, string>;
	filterOptions: Record<string, string[]>;
	isLoadingRows: boolean;
	rowsError: string | null;
	exploreQuery: string;
	exploreMatches: LedgerSearchMatch[];
	hasExplored: boolean;
	isExploring: boolean;
	exploreError: string | null;
	sql: string;
	queryResult: QueryResult | null;
	isRunningQuery: boolean;
	queryError: string | null;
	detailStack: LedgerDetail[];
	chain: LedgerChain | null;
	isLoadingChain: boolean;
	chainError: string | null;
}

export type LedgerDetail = {
	table: string;
	record: LedgerRecord;
};

const initialState: LedgerState = {
	fileName: "",
	tables: [],
	isLoading: false,
	error: null,
	view: "raw",
	selectedTable: "",
	search: "",
	rows: null,
	rowsTotal: 0,
	page: 0,
	filters: {},
	filterOptions: {},
	isLoadingRows: false,
	rowsError: null,
	exploreQuery: "",
	exploreMatches: [],
	hasExplored: false,
	isExploring: false,
	exploreError: null,
	sql: "",
	queryResult: null,
	isRunningQuery: false,
	queryError: null,
	detailStack: [],
	chain: null,
	isLoadingChain: false,
	chainError: null,
};

function clearLedger(state: LedgerState) {
	state.fileName = "";
	state.tables = [];
	state.selectedTable = "";
	state.search = "";
	state.rows = null;
	state.rowsTotal = 0;
	state.page = 0;
	state.filters = {};
	state.filterOptions = {};
	state.isLoadingRows = false;
	state.rowsError = null;
	state.exploreQuery = "";
	state.exploreMatches = [];
	state.hasExplored = false;
	state.isExploring = false;
	state.exploreError = null;
	state.sql = "";
	state.queryResult = null;
	state.isRunningQuery = false;
	state.queryError = null;
	state.detailStack = [];
	state.chain = null;
	state.isLoadingChain = false;
	state.chainError = null;
}

const ledgerSlice = createSlice({
	name: "ledger",
	initialState,
	reducers: {
		// The File is saga input only and is never held in state.
		openLedger: (state, _action: PayloadAction<File>) => {
			state.isLoading = true;
			state.error = null;
		},
		openLedgerSuccess: (
			state,
			action: PayloadAction<{ fileName: string; tables: LedgerTable[] }>,
		) => {
			state.isLoading = false;
			state.error = null;
			state.fileName = action.payload.fileName;
			state.tables = action.payload.tables;
			state.selectedTable = action.payload.tables[0]?.name ?? "";
			state.search = "";
			state.page = 0;
			state.filters = {};
			state.filterOptions = {};
			state.rows = null;
			state.rowsTotal = 0;
			state.rowsError = null;
		},
		openLedgerFailure: (state, action: PayloadAction<string>) => {
			state.isLoading = false;
			state.error = action.payload;
			clearLedger(state);
		},
		closeLedger: (state) => {
			state.isLoading = false;
			state.error = null;
			clearLedger(state);
		},
		setLedgerView: (state, action: PayloadAction<LedgerView>) => {
			state.view = action.payload;
		},
		selectLedgerTable: (state, action: PayloadAction<string>) => {
			state.selectedTable = action.payload;
			state.isLoadingRows = true;
			state.search = "";
			state.page = 0;
			state.filters = {};
			state.filterOptions = {};
			state.rows = null;
			state.rowsTotal = 0;
			state.rowsError = null;
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
		openTableWithSearch: (
			state,
			action: PayloadAction<{ table: string; search: string }>,
		) => {
			state.view = "raw";
			state.selectedTable = action.payload.table;
			state.isLoadingRows = true;
			state.search = action.payload.search;
			state.page = 0;
			state.filters = {};
			state.rows = null;
			state.rowsTotal = 0;
			state.rowsError = null;
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
			state.rows = null;
			state.rowsTotal = 0;
		},
		setExploreQuery: (state, action: PayloadAction<string>) => {
			state.exploreQuery = action.payload;
			if (action.payload.trim().length === 0) {
				state.exploreMatches = [];
				state.hasExplored = false;
				state.isExploring = false;
				state.exploreError = null;
			}
		},
		exploreLedger: (state) => {
			state.isExploring = true;
			state.exploreError = null;
		},
		exploreLedgerSuccess: (
			state,
			action: PayloadAction<LedgerSearchMatch[]>,
		) => {
			state.isExploring = false;
			state.exploreError = null;
			state.exploreMatches = action.payload;
			state.hasExplored = true;
		},
		exploreLedgerFailure: (state, action: PayloadAction<string>) => {
			state.isExploring = false;
			state.exploreError = action.payload;
			state.exploreMatches = [];
			state.hasExplored = true;
		},
		setLedgerSql: (state, action: PayloadAction<string>) => {
			state.sql = action.payload;
		},
		runLedgerQuery: (state) => {
			state.isRunningQuery = true;
			state.queryError = null;
		},
		runLedgerQuerySuccess: (state, action: PayloadAction<QueryResult>) => {
			state.isRunningQuery = false;
			state.queryError = null;
			state.queryResult = action.payload;
		},
		runLedgerQueryFailure: (state, action: PayloadAction<string>) => {
			state.isRunningQuery = false;
			state.queryError = action.payload;
			state.queryResult = null;
		},
		openLedgerDetail: (state, action: PayloadAction<LedgerDetail>) => {
			state.detailStack = [action.payload];
			state.isLoadingChain = true;
			state.chainError = null;
		},
		pushLedgerDetail: (state, action: PayloadAction<LedgerDetail>) => {
			state.detailStack.push(action.payload);
			state.isLoadingChain = true;
			state.chainError = null;
		},
		popLedgerDetail: (state) => {
			state.detailStack.pop();
			state.isLoadingChain = state.detailStack.length > 0;
			state.chainError = null;
		},
		closeLedgerDetail: (state) => {
			state.detailStack = [];
			state.chain = null;
			state.isLoadingChain = false;
			state.chainError = null;
		},
		resolveChainSuccess: (state, action: PayloadAction<LedgerChain>) => {
			state.isLoadingChain = false;
			state.chainError = null;
			state.chain = action.payload;
		},
		resolveChainFailure: (state, action: PayloadAction<string>) => {
			state.isLoadingChain = false;
			state.chainError = action.payload;
			state.chain = null;
		},
	},
});

export const {
	openLedger,
	openLedgerSuccess,
	openLedgerFailure,
	closeLedger,
	setLedgerView,
	selectLedgerTable,
	setLedgerSearch,
	loadLedgerRows,
	loadLedgerRowsSuccess,
	loadLedgerRowsFailure,
	setLedgerPage,
	setLedgerFilter,
	setLedgerFilterOptions,
	openTableWithSearch,
	setExploreQuery,
	exploreLedger,
	exploreLedgerSuccess,
	exploreLedgerFailure,
	setLedgerSql,
	runLedgerQuery,
	runLedgerQuerySuccess,
	runLedgerQueryFailure,
	openLedgerDetail,
	pushLedgerDetail,
	popLedgerDetail,
	closeLedgerDetail,
	resolveChainSuccess,
	resolveChainFailure,
} = ledgerSlice.actions;

export const selectLedgerFileName = (state: RootState) => state.ledger.fileName;
export const selectLedgerTables = (state: RootState) => state.ledger.tables;
export const selectIsLoadingLedger = (state: RootState) =>
	state.ledger.isLoading;
export const selectLedgerError = (state: RootState) => state.ledger.error;
export const selectHasLedger = (state: RootState) =>
	state.ledger.tables.length > 0;
export const selectLedgerView = (state: RootState) => state.ledger.view;
export const selectSelectedLedgerTable = (state: RootState) =>
	state.ledger.selectedTable;
export const selectLedgerSearch = (state: RootState) => state.ledger.search;
export const selectLedgerRows = (state: RootState) => state.ledger.rows;
export const selectIsLoadingLedgerRows = (state: RootState) =>
	state.ledger.isLoadingRows;
export const selectLedgerRowsError = (state: RootState) =>
	state.ledger.rowsError;
export const selectLedgerRowsTotal = (state: RootState) =>
	state.ledger.rowsTotal;
export const selectLedgerPage = (state: RootState) => state.ledger.page;
export const selectLedgerFilters = (state: RootState) => state.ledger.filters;
export const selectLedgerFilterOptions = (state: RootState) =>
	state.ledger.filterOptions;
export const selectExploreQuery = (state: RootState) =>
	state.ledger.exploreQuery;
export const selectExploreMatches = (state: RootState) =>
	state.ledger.exploreMatches;
export const selectHasExplored = (state: RootState) => state.ledger.hasExplored;
export const selectIsExploring = (state: RootState) => state.ledger.isExploring;
export const selectExploreError = (state: RootState) =>
	state.ledger.exploreError;
export const selectLedgerSql = (state: RootState) => state.ledger.sql;
export const selectLedgerQueryResult = (state: RootState) =>
	state.ledger.queryResult;
export const selectIsRunningLedgerQuery = (state: RootState) =>
	state.ledger.isRunningQuery;
export const selectLedgerQueryError = (state: RootState) =>
	state.ledger.queryError;

export const selectLedgerDetail = (state: RootState) =>
	state.ledger.detailStack.at(-1) ?? null;
export const selectCanGoBackLedgerDetail = (state: RootState) =>
	state.ledger.detailStack.length > 1;
export const selectLedgerChain = (state: RootState) => state.ledger.chain;
export const selectIsLoadingLedgerChain = (state: RootState) =>
	state.ledger.isLoadingChain;
export const selectLedgerChainError = (state: RootState) =>
	state.ledger.chainError;

export default ledgerSlice.reducer;
