import { createSlice, isAnyOf, type PayloadAction } from "@reduxjs/toolkit";
import { PREDEFINED_QUERIES } from "@/ledger/predefinedQueries";
import type { QueryResult } from "@/ledger/types";
import {
	closeLedger,
	openLedgerFailure,
	openLedgerSuccess,
} from "@/store/ledger/ledgerActions";
import type { RootState } from "@/store/types";

export interface LedgerQueryState {
	sql: string;
	predefinedQuery: string;
	queryResult: QueryResult | null;
	isRunningQuery: boolean;
	queryError: string | null;
}

const initialState: LedgerQueryState = {
	sql: "",
	predefinedQuery: "",
	queryResult: null,
	isRunningQuery: false,
	queryError: null,
};

const ledgerQuerySlice = createSlice({
	name: "ledgerQuery",
	initialState,
	reducers: {
		setLedgerSql: (state, action: PayloadAction<string>) => {
			state.sql = action.payload;
			// Edited SQL is no longer the query that was picked.
			state.predefinedQuery = "";
		},
		applyPredefinedQuery: (state, action: PayloadAction<string>) => {
			const query = PREDEFINED_QUERIES.find(
				(candidate) => candidate.label === action.payload,
			);
			if (!query) {
				return;
			}
			state.predefinedQuery = query.label;
			state.sql = query.sql;
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
	},
	extraReducers: (builder) => {
		builder.addMatcher(
			isAnyOf(closeLedger, openLedgerSuccess, openLedgerFailure),
			(state, action) => {
				if (openLedgerFailure.match(action) && !action.payload.cleared) {
					return;
				}
				Object.assign(state, initialState);
			},
		);
	},
});

export const {
	setLedgerSql,
	applyPredefinedQuery,
	runLedgerQuery,
	runLedgerQuerySuccess,
	runLedgerQueryFailure,
} = ledgerQuerySlice.actions;

export default ledgerQuerySlice.reducer;

export const selectLedgerSql = (state: RootState) => state.ledgerQuery.sql;
export const selectPredefinedQueryLabel = (state: RootState) =>
	state.ledgerQuery.predefinedQuery;
export const selectLedgerQueryResult = (state: RootState) =>
	state.ledgerQuery.queryResult;
export const selectIsRunningLedgerQuery = (state: RootState) =>
	state.ledgerQuery.isRunningQuery;
export const selectLedgerQueryError = (state: RootState) =>
	state.ledgerQuery.queryError;
