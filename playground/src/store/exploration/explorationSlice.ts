import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { SchemaReference } from "@/api/types";
import {
	fetchDependenciesConfigSuccess,
	removeDependency,
} from "@/store/deps/depsSlice";
import type { RootState } from "@/store/types";
import type { DependencyDraft } from "@/types/dependency";

export type ExplorationSnapshot = {
	originalSchema: string;
	originalSchemaReference: SchemaReference | null;
	filteredSchema: string;
	selectionQuery: string;
	appliedSelectionQuery: string;
};

export interface ExplorationState {
	exploringDependencyId: string | null;
	snapshot: ExplorationSnapshot | null;
}

const initialState: ExplorationState = {
	exploringDependencyId: null,
	snapshot: null,
};

const explorationSlice = createSlice({
	name: "exploration",
	initialState,
	reducers: {
		startDependencyExploration: (
			state,
			action: PayloadAction<DependencyDraft>,
		) => {
			state.exploringDependencyId = action.payload.id;
		},
		exitExploration: (state) => {
			state.exploringDependencyId = null;
		},
		setExplorationSnapshot: (
			state,
			action: PayloadAction<ExplorationSnapshot | null>,
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
	exitExploration,
	setExplorationSnapshot,
} = explorationSlice.actions;

export const selectExploringDependencyId = (state: RootState) =>
	state.exploration.exploringDependencyId;
export const selectIsExploring = (state: RootState) =>
	state.exploration.exploringDependencyId !== null;
export const selectExplorationSnapshot = (state: RootState) =>
	state.exploration.snapshot;

export default explorationSlice.reducer;
