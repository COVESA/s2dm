import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import {
	addDependency,
	fetchDependenciesConfig,
	removeDependency,
	saveDependenciesConfig,
	updateDependency,
	updateDependencyField,
} from "@/store/deps/depsSlice";
import { resolveDependencies } from "@/store/deps/resolve/resolveSlice";
import type { RootState } from "@/store/types";

export interface DepsComposeState {
	isComposing: boolean;
	composedSchema: string | null;
	message: string | null;
	error: string | null;
}

const initialState: DepsComposeState = {
	isComposing: false,
	composedSchema: null,
	message: null,
	error: null,
};

const composeSlice = createSlice({
	name: "depsCompose",
	initialState,
	reducers: {
		composeDependencies: (
			state,
			_action: PayloadAction<{ autoPrefix: boolean }>,
		) => {
			state.isComposing = true;
			state.message = null;
			state.error = null;
		},
		composeDependenciesSuccess: (state, action: PayloadAction<string>) => {
			state.isComposing = false;
			state.composedSchema = action.payload;
			state.message = "Dependencies built successfully.";
			state.error = null;
		},
		composeDependenciesFailure: (state, action: PayloadAction<string>) => {
			state.isComposing = false;
			state.composedSchema = null;
			state.error = action.payload;
		},
		clearComposeMessage: (state) => {
			state.message = null;
		},
	},
	extraReducers: (builder) => {
		const clearMessage = (state: DepsComposeState) => {
			state.message = null;
		};
		builder.addCase(addDependency, clearMessage);
		builder.addCase(updateDependency, clearMessage);
		builder.addCase(removeDependency, clearMessage);
		builder.addCase(updateDependencyField, clearMessage);
		builder.addCase(fetchDependenciesConfig, clearMessage);
		builder.addCase(saveDependenciesConfig, clearMessage);
		builder.addCase(resolveDependencies, clearMessage);
	},
});

export const {
	composeDependencies,
	composeDependenciesSuccess,
	composeDependenciesFailure,
	clearComposeMessage,
} = composeSlice.actions;

export const selectIsComposing = (state: RootState) =>
	state.depsCompose.isComposing;
export const selectComposedDependenciesSchema = (state: RootState) =>
	state.depsCompose.composedSchema;
export const selectHasComposedDependenciesSchema = (state: RootState) =>
	Boolean(state.depsCompose.composedSchema?.trim());
export const selectComposeMessage = (state: RootState) =>
	state.depsCompose.message;
export const selectComposeError = (state: RootState) => state.depsCompose.error;

export default composeSlice.reducer;
