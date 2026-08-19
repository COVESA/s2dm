import {
	openInsightDetail,
	pushInsightDetail,
} from "@insights-ui/state/insightDetailSlice";
import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import { openLedgerDetail, pushLedgerDetail } from "@/store/ledger/ledgerSlice";
import type { RootState } from "@/store/types";

export type Workspace = "schema" | "ledger";

export type ExploreTab = "explorer" | "insights";

export interface UIState {
	panes: {
		input: {
			isCollapsed: boolean;
		};
		result: {
			isCollapsed: boolean;
		};
	};
	workspace: Workspace;
	exploreTab: ExploreTab;
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
	workspace: "schema",
	exploreTab: "explorer",
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
		collapseResultPane: (state) => {
			state.panes.result.isCollapsed = true;
		},
		setWorkspace: (state, action: PayloadAction<Workspace>) => {
			state.workspace = action.payload;
		},
		setExploreTab: (state, action: PayloadAction<ExploreTab>) => {
			state.exploreTab = action.payload;
		},
	},
	extraReducers: (builder) => {
		// Opening a detail reveals it in the result pane, which starts collapsed.
		builder
			.addCase(openInsightDetail, (state) => {
				state.panes.result.isCollapsed = false;
			})
			.addCase(pushInsightDetail, (state) => {
				state.panes.result.isCollapsed = false;
			})
			.addCase(openLedgerDetail, (state) => {
				state.panes.result.isCollapsed = false;
			})
			.addCase(pushLedgerDetail, (state) => {
				state.panes.result.isCollapsed = false;
			});
	},
});

export const {
	toggleInputPane,
	toggleResultPane,
	collapseResultPane,
	setWorkspace,
	setExploreTab,
} = uiSlice.actions;

export const selectInputPaneCollapsed = (state: RootState) =>
	state.ui.panes.input.isCollapsed;
export const selectResultPaneCollapsed = (state: RootState) =>
	state.ui.panes.result.isCollapsed;
export const selectWorkspace = (state: RootState) => state.ui.workspace;
export const selectExploreTab = (state: RootState) => state.ui.exploreTab;

export default uiSlice.reducer;
