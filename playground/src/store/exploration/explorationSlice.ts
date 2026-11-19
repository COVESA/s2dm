import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { SchemaReference } from "@/api/types";
import {
	fetchDependenciesConfigSuccess,
	removeDependency,
} from "@/store/deps/depsSlice";
import type { RootState } from "@/store/types";
import type { DependencyDraft } from "@/types/dependency";
import type { LoadedRelease } from "@/types/release";

export type ExplorationSnapshot = {
	originalSchema: string;
	originalSchemaReference: SchemaReference | null;
	filteredSchema: string;
	selectionQuery: string;
	appliedSelectionQuery: string;
};

export interface ExplorationState {
	exploringDependencyId: string | null;
	exploringReleaseId: string | null;
	snapshot: ExplorationSnapshot | null;
}

const initialState: ExplorationState = {
	exploringDependencyId: null,
	exploringReleaseId: null,
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
			state.exploringReleaseId = null;
		},
		startReleaseExploration: (state, action: PayloadAction<LoadedRelease>) => {
			state.exploringReleaseId = action.payload.id;
			state.exploringDependencyId = null;
		},
		exitExploration: (state) => {
			state.exploringDependencyId = null;
			state.exploringReleaseId = null;
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
			if (state.exploringDependencyId === null) {
				return;
			}
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
	startReleaseExploration,
	exitExploration,
	setExplorationSnapshot,
} = explorationSlice.actions;

export const selectExploringDependencyId = (state: RootState) =>
	state.exploration.exploringDependencyId;
export const selectExploringReleaseId = (state: RootState) =>
	state.exploration.exploringReleaseId;
export const selectIsExploring = (state: RootState) =>
	state.exploration.exploringDependencyId !== null ||
	state.exploration.exploringReleaseId !== null;
export const selectExplorationSnapshot = (state: RootState) =>
	state.exploration.snapshot;

/** Gives the schema of the explored dependency or release, if any. */
export const selectExploredSchemaContent = (
	state: RootState,
): string | null | undefined => {
	const { exploringDependencyId, exploringReleaseId } = state.exploration;
	const exploringRelease = state.releases.loadedReleases.find(
		(loadedRelease) => loadedRelease.id === exploringReleaseId,
	);
	if (exploringRelease) {
		return exploringRelease.schemaContent;
	}

	const exploringDependency = state.deps.dependencies.find(
		(dependency) => dependency.id === exploringDependencyId,
	);
	return exploringDependency?.schemaContent;
};

export default explorationSlice.reducer;
