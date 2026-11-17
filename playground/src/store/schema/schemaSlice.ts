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
	/** The paths of the source files that the last successful compose used. */
	composedFilePaths: string[];
	includeBuiltDependencies: boolean;
	importError: string | null;
}

const initialState: SchemaState = {
	original: "",
	originalReference: null,
	filtered: "",
	sourceFiles: [],
	composedFilePaths: [],
	includeBuiltDependencies: false,
	importError: null,
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
		setComposedFilePaths: (state, action: PayloadAction<string[]>) => {
			state.composedFilePaths = action.payload;
		},
		setIncludeBuiltDependencies: (state, action: PayloadAction<boolean>) => {
			state.includeBuiltDependencies = action.payload;
		},
		setImportError: (state, action: PayloadAction<string | null>) => {
			state.importError = action.payload;
		},
		resetSchema: () => initialState,
	},
});

export const {
	setOriginalSchema,
	setFilteredSchema,
	setSourceFiles,
	setComposedFilePaths,
	setIncludeBuiltDependencies,
	setImportError,
	resetSchema,
} = schemaSlice.actions;

export const selectOriginalSchema = (state: RootState) => state.schema.original;
export const selectOriginalSchemaReference = (state: RootState) =>
	state.schema.originalReference;
export const selectHasSchema = (state: RootState) =>
	state.schema.original.trim().length > 0;
export const selectFilteredSchema = (state: RootState) => state.schema.filtered;
export const selectSourceFiles = (state: RootState) => state.schema.sourceFiles;
export const selectComposedFilePaths = (state: RootState) =>
	state.schema.composedFilePaths;
export const selectIncludeBuiltDependencies = (state: RootState) =>
	state.schema.includeBuiltDependencies;
export const selectImportError = (state: RootState) => state.schema.importError;

export default schemaSlice.reducer;
