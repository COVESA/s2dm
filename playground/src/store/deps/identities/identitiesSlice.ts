import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { DependenciesIdentities } from "@/api/types";
import type { RootState } from "@/store/types";
import {
	areDependencyIdentityDraftsEqual,
	type DependencyIdentityDraft,
} from "@/types/dependencyIdentity";

export interface DepsIdentitiesState {
	identities: DependencyIdentityDraft[];
	storedIdentities: DependencyIdentityDraft[];
	isLoading: boolean;
	isImporting: boolean;
	isSaving: boolean;
	error: string | null;
}

const initialState: DepsIdentitiesState = {
	identities: [],
	storedIdentities: [],
	isLoading: false,
	isImporting: false,
	isSaving: false,
	error: null,
};

const identitiesSlice = createSlice({
	name: "depsIdentities",
	initialState,
	reducers: {
		fetchIdentities: (state) => {
			state.isLoading = true;
			state.error = null;
		},
		fetchIdentitiesSuccess: (
			state,
			action: PayloadAction<DependencyIdentityDraft[]>,
		) => {
			state.isLoading = false;
			state.identities = action.payload;
			state.storedIdentities = action.payload.map((draft) => ({ ...draft }));
			state.error = null;
		},
		fetchIdentitiesFailure: (state, action: PayloadAction<string>) => {
			state.isLoading = false;
			state.error = action.payload;
		},
		importIdentitiesFile: (
			state,
			_action: PayloadAction<DependenciesIdentities>,
		) => {
			state.isImporting = true;
			state.error = null;
		},
		importIdentitiesFileSuccess: (state) => {
			state.isImporting = false;
			state.error = null;
		},
		importIdentitiesFileFailure: (state, action: PayloadAction<string>) => {
			state.isImporting = false;
			state.error = action.payload;
		},
		addIdentity: (state, action: PayloadAction<DependencyIdentityDraft>) => {
			state.identities.unshift(action.payload);
			state.error = null;
		},
		updateIdentity: (state, action: PayloadAction<DependencyIdentityDraft>) => {
			const identityIndex = state.identities.findIndex(
				(identity) => identity.id === action.payload.id,
			);
			if (identityIndex === -1) {
				return;
			}

			state.identities[identityIndex] = action.payload;
			state.error = null;
		},
		removeIdentity: (state, action: PayloadAction<string>) => {
			state.identities = state.identities.filter(
				(identity) => identity.id !== action.payload,
			);
			state.error = null;
		},
		saveIdentities: (state) => {
			state.isSaving = true;
			state.error = null;
		},
		saveIdentitiesSuccess: (state) => {
			state.isSaving = false;
			state.storedIdentities = state.identities.map((draft) => ({ ...draft }));
			state.error = null;
		},
		saveIdentitiesFailure: (state, action: PayloadAction<string>) => {
			state.isSaving = false;
			state.error = action.payload;
		},
	},
});

export const {
	fetchIdentities,
	fetchIdentitiesSuccess,
	fetchIdentitiesFailure,
	importIdentitiesFile,
	importIdentitiesFileSuccess,
	importIdentitiesFileFailure,
	addIdentity,
	updateIdentity,
	removeIdentity,
	saveIdentities,
	saveIdentitiesSuccess,
	saveIdentitiesFailure,
} = identitiesSlice.actions;

export const selectIdentityDrafts = (state: RootState) =>
	state.depsIdentities.identities;
export const selectIsLoadingIdentities = (state: RootState) =>
	state.depsIdentities.isLoading;
export const selectIsImportingIdentities = (state: RootState) =>
	state.depsIdentities.isImporting;
export const selectIsSavingIdentities = (state: RootState) =>
	state.depsIdentities.isSaving;
export const selectIdentitiesError = (state: RootState) =>
	state.depsIdentities.error;
export const selectHasUnsavedIdentityChanges = (state: RootState) =>
	!areDependencyIdentityDraftsEqual(
		state.depsIdentities.storedIdentities,
		state.depsIdentities.identities,
	);

export default identitiesSlice.reducer;
