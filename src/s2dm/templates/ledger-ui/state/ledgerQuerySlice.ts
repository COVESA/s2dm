import { PREDEFINED_QUERIES } from "@ledger-ui/data/predefinedQueries";
import type { QueryResult } from "@ledger-ui/data/types";
import {
	closeLedger,
	openLedgerFailure,
	openLedgerSuccess,
} from "@ledger-ui/state/ledgerActions";
import type { LedgerRootState } from "@ledger-ui/state/types";
import { createSlice, isAnyOf, type PayloadAction } from "@reduxjs/toolkit";

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

export const selectLedgerSql = (state: LedgerRootState) =>
	state.ledgerQuery.sql;
export const selectPredefinedQueryLabel = (state: LedgerRootState) =>
	state.ledgerQuery.predefinedQuery;
export const selectLedgerQueryResult = (state: LedgerRootState) =>
	state.ledgerQuery.queryResult;
export const selectIsRunningLedgerQuery = (state: LedgerRootState) =>
	state.ledgerQuery.isRunningQuery;
export const selectLedgerQueryError = (state: LedgerRootState) =>
	state.ledgerQuery.queryError;
