import { createSlice } from "@reduxjs/toolkit";
import type { RootState } from "@/store/types";

export interface UIState {
	panes: {
		input: {
			isCollapsed: boolean;
		};
		result: {
			isCollapsed: boolean;
		};
	};
}

const initialState: UIState = {
	panes: {
		input: {
			isCollapsed: false,
		},
		result: {
			isCollapsed: true,
		},
	},
};

const uiSlice = createSlice({
	name: "ui",
	initialState,
	reducers: {
		toggleInputPane: (state) => {
			state.panes.input.isCollapsed = !state.panes.input.isCollapsed;
		},
		toggleResultPane: (state) => {
			state.panes.result.isCollapsed = !state.panes.result.isCollapsed;
		},
	},
});

export const { toggleInputPane, toggleResultPane } = uiSlice.actions;

export const selectInputPaneCollapsed = (state: RootState) =>
	state.ui.panes.input.isCollapsed;
export const selectResultPaneCollapsed = (state: RootState) =>
	state.ui.panes.result.isCollapsed;

export default uiSlice.reducer;
