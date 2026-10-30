import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import type { SchemaReference } from "@/api/types";
import type { RootState } from "@/store/types";
import type { ImportedFile } from "@/types/importedFile";

export type OriginalSchemaPayload = {
	schema: string;
	reference: SchemaReference | null;
};

export interface SchemaState {
	original: string;
	originalReference: SchemaReference | null;
	filtered: string;
	sourceFiles: ImportedFile[];
	includeBuiltDependencies: boolean;
}

const initialState: SchemaState = {
	original: "",
	originalReference: null,
	filtered: "",
	sourceFiles: [],
	includeBuiltDependencies: false,
};

const schemaSlice = createSlice({
	name: "schema",
	initialState,
	reducers: {
		setOriginalSchema: (
			state,
			action: PayloadAction<OriginalSchemaPayload>,
		) => {
			state.original = action.payload.schema;
			state.originalReference = action.payload.reference;
			state.filtered = action.payload.schema;
		},
		setFilteredSchema: (state, action: PayloadAction<string>) => {
			state.filtered = action.payload;
		},
		setSourceFiles: (state, action: PayloadAction<ImportedFile[]>) => {
			state.sourceFiles = action.payload;
		},
		setIncludeBuiltDependencies: (state, action: PayloadAction<boolean>) => {
			state.includeBuiltDependencies = action.payload;
		},
		resetSchema: () => initialState,
	},
});

export const {
	setOriginalSchema,
	setFilteredSchema,
	setSourceFiles,
	setIncludeBuiltDependencies,
	resetSchema,
} = schemaSlice.actions;

export const selectOriginalSchema = (state: RootState) => state.schema.original;
export const selectOriginalSchemaReference = (state: RootState) =>
	state.schema.originalReference;
export const selectHasSchema = (state: RootState) =>
	state.schema.original.trim().length > 0;
export const selectFilteredSchema = (state: RootState) => state.schema.filtered;
export const selectSourceFiles = (state: RootState) => state.schema.sourceFiles;
export const selectIncludeBuiltDependencies = (state: RootState) =>
	state.schema.includeBuiltDependencies;

export default schemaSlice.reducer;
