import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import {
	fetchDependenciesConfigSuccess,
	removeDependency,
} from "@/store/deps/depsSlice";
import type { RootState } from "@/store/types";
import type { DependencyDraft } from "@/types/dependency";

export type DependencyExplorationSnapshot = {
	originalSchema: string;
	filteredSchema: string;
	selectionQuery: string;
	appliedSelectionQuery: string;
};

export interface DependencyExplorationState {
	exploringDependencyId: string | null;
	snapshot: DependencyExplorationSnapshot | null;
}

const initialState: DependencyExplorationState = {
	exploringDependencyId: null,
	snapshot: null,
};

const dependencyExplorationSlice = createSlice({
	name: "dependencyExploration",
	initialState,
	reducers: {
		startDependencyExploration: (
			state,
			action: PayloadAction<DependencyDraft>,
		) => {
			state.exploringDependencyId = action.payload.id;
		},
		exitDependencyExploration: (state) => {
			state.exploringDependencyId = null;
		},
		setDependencyExplorationSnapshot: (
			state,
			action: PayloadAction<DependencyExplorationSnapshot | null>,
		) => {
			state.snapshot = action.payload;
		},
	},
	extraReducers: (builder) => {
		builder.addCase(fetchDependenciesConfigSuccess, (state, action) => {
			const hasExploringDependency = action.payload.some(
				(dependency) => dependency.id === state.exploringDependencyId,
			);
			if (!hasExploringDependency) {
				state.exploringDependencyId = null;
				state.snapshot = null;
			}
		});
		builder.addCase(removeDependency, (state, action) => {
			if (state.exploringDependencyId === action.payload) {
				state.exploringDependencyId = null;
				state.snapshot = null;
			}
		});
	},
});

export const {
	startDependencyExploration,
	exitDependencyExploration,
	setDependencyExplorationSnapshot,
} = dependencyExplorationSlice.actions;

export const selectExploringDependencyId = (state: RootState) =>
	state.dependencyExploration.exploringDependencyId;
export const selectDependencyExplorationSnapshot = (state: RootState) =>
	state.dependencyExploration.snapshot;

export default dependencyExplorationSlice.reducer;
