import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import type { RootState } from "@/store/types";

export interface SelectionState {
	query: string;
	appliedQuery: string;
	isPruning: boolean;
	error: string | null;
}

const initialState: SelectionState = {
	query: "",
	appliedQuery: "",
	isPruning: false,
	error: null,
};

const selectionSlice = createSlice({
	name: "selection",
	initialState,
	reducers: {
		setSelectionQuery: (state, action: PayloadAction<string>) => {
			state.query = action.payload;
			state.error = null;
		},
		clearAppliedSelection: (state) => {
			state.appliedQuery = "";
			state.error = null;
		},
		setAppliedSelectionQuery: (state, action: PayloadAction<string>) => {
			state.appliedQuery = action.payload;
			state.error = null;
		},
		resetSelection: (state) => {
			state.query = "";
			state.appliedQuery = "";
			state.error = null;
		},
		pruningStart: (state, _action: PayloadAction<string>) => {
			state.isPruning = true;
			state.error = null;
		},
		pruningSuccess: (state, action: PayloadAction<string>) => {
			state.isPruning = false;
			state.appliedQuery = action.payload;
		},
		pruningFailure: (state, action: PayloadAction<string>) => {
			state.isPruning = false;
			state.error = action.payload;
		},
	},
});

export const {
	clearAppliedSelection,
	resetSelection,
	setSelectionQuery,
	setAppliedSelectionQuery,
	pruningStart,
	pruningSuccess,
	pruningFailure,
} = selectionSlice.actions;

export const selectSelectionQuery = (state: RootState) => state.selection.query;
export const selectAppliedSelectionQuery = (state: RootState) =>
	state.selection.appliedQuery;
export const selectIsPruning = (state: RootState) => state.selection.isPruning;
export const selectPruningError = (state: RootState) => state.selection.error;

export default selectionSlice.reducer;
