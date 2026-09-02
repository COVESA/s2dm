import { createSlice, isAnyOf, type PayloadAction } from "@reduxjs/toolkit";
import type { LedgerChain } from "@/ledger/chainSpec";
import type { LedgerRecord, LedgerValue } from "@/ledger/types";
import {
	closeLedger,
	openLedgerFailure,
	openLedgerSuccess,
} from "@/store/ledger/ledgerActions";
import type { RootState } from "@/store/types";

export type LedgerCell = { column: string; value: LedgerValue };

export type LedgerDetail =
	| { kind: "row"; table: string; record: LedgerRecord }
	// A query projection: real values, but not a row of any ledger table. The
	// cells are positional, so a repeated column name survives.
	| { kind: "projection"; record: LedgerRecord; cells: LedgerCell[] };

export interface LedgerDetailState {
	detailStack: LedgerDetail[];
	chain: LedgerChain | null;
	isLoadingChain: boolean;
	chainError: string | null;
}

const initialState: LedgerDetailState = {
	detailStack: [],
	chain: null,
	isLoadingChain: false,
	chainError: null,
};

const ledgerDetailSlice = createSlice({
	name: "ledgerDetail",
	initialState,
	reducers: {
		viewLedgerRecord: (
			state,
			_action: PayloadAction<{ table: string; column: string; value: string }>,
		) => {
			state.isLoadingChain = true;
			state.chainError = null;
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
		clearLedgerChain: (state) => {
			state.isLoadingChain = false;
			state.chain = null;
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
	viewLedgerRecord,
	openLedgerDetail,
	pushLedgerDetail,
	popLedgerDetail,
	closeLedgerDetail,
	clearLedgerChain,
	resolveChainSuccess,
	resolveChainFailure,
} = ledgerDetailSlice.actions;

export default ledgerDetailSlice.reducer;

export const selectLedgerDetail = (state: RootState) =>
	state.ledgerDetail.detailStack.at(-1) ?? null;
export const selectCanGoBackLedgerDetail = (state: RootState) =>
	state.ledgerDetail.detailStack.length > 1;
export const selectLedgerChain = (state: RootState) => state.ledgerDetail.chain;
export const selectIsLoadingLedgerChain = (state: RootState) =>
	state.ledgerDetail.isLoadingChain;
export const selectLedgerChainError = (state: RootState) =>
	state.ledgerDetail.chainError;
