import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import {
	addDependency,
	fetchDependenciesConfig,
	removeDependency,
	updateDependency,
	updateDependencyField,
} from "@/store/deps/depsSlice";
import type { RootState } from "@/store/types";

export interface DepsResolveState {
	isResolving: boolean;
	warnings: string[];
	error: string | null;
	cleanBeforeResolve: boolean;
}

const initialState: DepsResolveState = {
	isResolving: false,
	warnings: [],
	error: null,
	cleanBeforeResolve: false,
};

const resolveSlice = createSlice({
	name: "depsResolve",
	initialState,
	reducers: {
		resolveDependencies: (state) => {
			state.isResolving = true;
			state.warnings = [];
			state.error = null;
		},
		setCleanBeforeResolve: (state, action: PayloadAction<boolean>) => {
			state.cleanBeforeResolve = action.payload;
		},
		resolveDependenciesSuccess: (state, action: PayloadAction<string[]>) => {
			state.isResolving = false;
			state.warnings = action.payload;
			state.error = null;
		},
		resolveDependenciesFailure: (state, action: PayloadAction<string>) => {
			state.isResolving = false;
			state.error = action.payload;
		},
	},
	extraReducers: (builder) => {
		const clearWarnings = (state: DepsResolveState) => {
			state.warnings = [];
		};
		builder.addCase(addDependency, clearWarnings);
		builder.addCase(updateDependency, clearWarnings);
		builder.addCase(removeDependency, clearWarnings);
		builder.addCase(updateDependencyField, clearWarnings);
		builder.addCase(fetchDependenciesConfig, clearWarnings);
	},
});

export const {
	resolveDependencies,
	resolveDependenciesSuccess,
	resolveDependenciesFailure,
	setCleanBeforeResolve,
} = resolveSlice.actions;

export const selectIsResolvingDependencies = (state: RootState) =>
	state.depsResolve.isResolving;
export const selectResolveWarnings = (state: RootState) =>
	state.depsResolve.warnings;
export const selectResolveError = (state: RootState) => state.depsResolve.error;
export const selectCleanBeforeResolve = (state: RootState) =>
	state.depsResolve.cleanBeforeResolve;

export default resolveSlice.reducer;
