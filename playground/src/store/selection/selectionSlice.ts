import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import type { RootState } from "@/store/types";

export interface SelectionState {
	query: string;
	isPruning: boolean;
	error: string | null;
}

const initialState: SelectionState = {
	query: "",
	isPruning: false,
	error: null,
};

const selectionSlice = createSlice({
	name: "selection",
	initialState,
	reducers: {
		resetSelectionQuery: (state) => {
			state.query = "";
			state.error = null;
		},
		pruningStart: (state, _action: PayloadAction<string>) => {
			state.isPruning = true;
			state.error = null;
		},
		pruningSuccess: (state, action: PayloadAction<string>) => {
			state.isPruning = false;
			state.query = action.payload;
		},
		pruningFailure: (state, action: PayloadAction<string>) => {
			state.isPruning = false;
			state.error = action.payload;
		},
	},
});

export const {
	resetSelectionQuery,
	pruningStart,
	pruningSuccess,
	pruningFailure,
} = selectionSlice.actions;

export const selectSelectionQuery = (state: RootState) => state.selection.query;
export const selectIsPruning = (state: RootState) => state.selection.isPruning;
export const selectPruningError = (state: RootState) => state.selection.error;

export default selectionSlice.reducer;
