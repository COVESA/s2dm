import { createSlice, isAnyOf, type PayloadAction } from "@reduxjs/toolkit";
import type { LedgerSearchMatch } from "@/ledger/types";
import {
	closeLedger,
	openLedgerFailure,
	openLedgerSuccess,
} from "@/store/ledger/ledgerActions";
import type { RootState } from "@/store/types";

export interface LedgerExploreState {
	exploreQuery: string;
	exploreMatches: LedgerSearchMatch[];
	hasExplored: boolean;
	isExploring: boolean;
	exploreError: string | null;
}

const initialState: LedgerExploreState = {
	exploreQuery: "",
	exploreMatches: [],
	hasExplored: false,
	isExploring: false,
	exploreError: null,
};

const ledgerExploreSlice = createSlice({
	name: "ledgerExplore",
	initialState,
	reducers: {
		setExploreQuery: (state, action: PayloadAction<string>) => {
			state.exploreQuery = action.payload;
			state.exploreError = null;
			if (action.payload.trim().length === 0) {
				state.exploreMatches = [];
				state.hasExplored = false;
				state.isExploring = false;
				return;
			}
			// From this keystroke, not the debounce: the previous needle's matches
			// must not sit under the text now in the box.
			state.isExploring = true;
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
	setExploreQuery,
	exploreLedger,
	exploreLedgerSuccess,
	exploreLedgerFailure,
} = ledgerExploreSlice.actions;

export default ledgerExploreSlice.reducer;

export const selectExploreQuery = (state: RootState) =>
	state.ledgerExplore.exploreQuery;
export const selectExploreMatches = (state: RootState) =>
	state.ledgerExplore.exploreMatches;
export const selectHasExplored = (state: RootState) =>
	state.ledgerExplore.hasExplored;
export const selectIsExploring = (state: RootState) =>
	state.ledgerExplore.isExploring;
export const selectExploreError = (state: RootState) =>
	state.ledgerExplore.exploreError;
