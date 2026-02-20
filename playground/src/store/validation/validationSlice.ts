import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import type { RootState } from "@/store/types";
import type { ImportedFile } from "@/types/importedFile";

export interface ValidationState {
	isValidating: boolean;
	errors: string[];
}

const initialState: ValidationState = {
	isValidating: false,
	errors: [],
};

const validationSlice = createSlice({
	name: "validation",
	initialState,
	reducers: {
		validateAndCompose: (state, _action: PayloadAction<ImportedFile[]>) => {
			state.isValidating = true;
			state.errors = [];
		},
		validationSuccess: (state) => {
			state.isValidating = false;
			state.errors = [];
		},
		validationFailure: (state, action: PayloadAction<string[]>) => {
			state.isValidating = false;
			state.errors = action.payload;
		},
		clearValidationErrors: (state) => {
			state.errors = [];
		},
	},
});

export const {
	validateAndCompose,
	validationSuccess,
	validationFailure,
	clearValidationErrors,
} = validationSlice.actions;

export const selectIsValidating = (state: RootState) =>
	state.validation.isValidating;
export const selectValidationErrors = (state: RootState) =>
	state.validation.errors;

export default validationSlice.reducer;
