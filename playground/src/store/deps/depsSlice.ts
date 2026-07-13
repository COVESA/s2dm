import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type {
	DependencyStatus,
	SaveDependenciesConfigRequest,
} from "@/api/types";
import type { RootState } from "@/store/types";
import {
	areDependencyDraftsEqual,
	type DependencyDraft,
	type DependencyEditableField,
} from "@/types/dependency";

export interface DepsState {
	status: DependencyStatus | null;
	statusError: string | null;
	isLoadingStatus: boolean;
	dependencies: DependencyDraft[];
	storedDependencies: DependencyDraft[];
	isLoadingConfig: boolean;
	isImportingConfig: boolean;
	isSavingConfig: boolean;
	error: string | null;
}

const initialState: DepsState = {
	status: null,
	statusError: null,
	isLoadingStatus: false,
	dependencies: [],
	storedDependencies: [],
	isLoadingConfig: false,
	isImportingConfig: false,
	isSavingConfig: false,
	error: null,
};

const depsSlice = createSlice({
	name: "deps",
	initialState,
	reducers: {
		fetchDependenciesStatus: (state) => {
			state.isLoadingStatus = true;
			state.statusError = null;
		},
		fetchDependenciesStatusSuccess: (
			state,
			action: PayloadAction<DependencyStatus>,
		) => {
			state.isLoadingStatus = false;
			state.status = action.payload;
			state.statusError = null;
		},
		fetchDependenciesStatusFailure: (state, action: PayloadAction<string>) => {
			state.isLoadingStatus = false;
			state.statusError = action.payload;
		},
		fetchDependenciesConfig: (state) => {
			state.isLoadingConfig = true;
			state.error = null;
		},
		fetchDependenciesConfigSuccess: (
			state,
			action: PayloadAction<DependencyDraft[]>,
		) => {
			state.isLoadingConfig = false;
			state.dependencies = action.payload;
			state.storedDependencies = action.payload.map((draft) => ({ ...draft }));
			state.error = null;
		},
		fetchDependenciesConfigFailure: (state, action: PayloadAction<string>) => {
			state.isLoadingConfig = false;
			state.error = action.payload;
		},
		importDependenciesConfig: (
			state,
			_action: PayloadAction<SaveDependenciesConfigRequest>,
		) => {
			state.isImportingConfig = true;
			state.error = null;
		},
		importDependenciesConfigSuccess: (state) => {
			state.isImportingConfig = false;
			state.error = null;
		},
		importDependenciesConfigFailure: (state, action: PayloadAction<string>) => {
			state.isImportingConfig = false;
			state.error = action.payload;
		},
		clearDependenciesError: (state) => {
			state.error = null;
		},
		addDependency: (state, action: PayloadAction<DependencyDraft>) => {
			state.dependencies.unshift(action.payload);
			state.error = null;
		},
		updateDependency: (state, action: PayloadAction<DependencyDraft>) => {
			const dependencyIndex = state.dependencies.findIndex(
				(dependency) => dependency.id === action.payload.id,
			);
			if (dependencyIndex === -1) {
				return;
			}

			state.dependencies[dependencyIndex] = action.payload;
			state.error = null;
		},
		removeDependency: (state, action: PayloadAction<string>) => {
			state.dependencies = state.dependencies.filter(
				(dependency) => dependency.id !== action.payload,
			);
			state.error = null;
		},
		updateDependencyField: (
			state,
			action: PayloadAction<{
				dependencyId: string;
				field: DependencyEditableField;
				value: string;
			}>,
		) => {
			const dependency = state.dependencies.find(
				(draft) => draft.id === action.payload.dependencyId,
			);
			if (!dependency) {
				return;
			}

			if (action.payload.field === "selectionContent") {
				dependency.selectionType = action.payload.value.trim()
					? "content"
					: null;
				dependency.selectionContent = action.payload.value;
			} else {
				dependency[action.payload.field] = action.payload.value;
			}

			state.error = null;
		},
		saveDependenciesConfig: (state) => {
			state.isSavingConfig = true;
			state.error = null;
		},
		saveDependenciesConfigSuccess: (state) => {
			state.isSavingConfig = false;
			state.storedDependencies = state.dependencies.map((draft) => ({
				...draft,
			}));
			state.error = null;
		},
		saveDependenciesConfigFailure: (state, action: PayloadAction<string>) => {
			state.isSavingConfig = false;
			state.error = action.payload;
		},
	},
});

export const {
	fetchDependenciesStatus,
	fetchDependenciesStatusSuccess,
	fetchDependenciesStatusFailure,
	fetchDependenciesConfig,
	fetchDependenciesConfigSuccess,
	fetchDependenciesConfigFailure,
	importDependenciesConfig,
	importDependenciesConfigSuccess,
	importDependenciesConfigFailure,
	clearDependenciesError,
	addDependency,
	updateDependency,
	removeDependency,
	updateDependencyField,
	saveDependenciesConfig,
	saveDependenciesConfigSuccess,
	saveDependenciesConfigFailure,
} = depsSlice.actions;

export const selectDependencyStatus = (state: RootState) => state.deps.status;
export const selectDependencyStatusError = (state: RootState) =>
	state.deps.statusError;
export const selectIsLoadingDependencyStatus = (state: RootState) =>
	state.deps.isLoadingStatus;
export const selectDependencyDrafts = (state: RootState) =>
	state.deps.dependencies;
export const selectIsLoadingDependenciesConfig = (state: RootState) =>
	state.deps.isLoadingConfig;
export const selectIsImportingDependenciesConfig = (state: RootState) =>
	state.deps.isImportingConfig;
export const selectIsSavingDependenciesConfig = (state: RootState) =>
	state.deps.isSavingConfig;
export const selectDependenciesError = (state: RootState) => state.deps.error;
export const selectHasUnsavedDependencyChanges = (state: RootState) =>
	!areDependencyDraftsEqual(
		state.deps.storedDependencies,
		state.deps.dependencies,
	);

export default depsSlice.reducer;
