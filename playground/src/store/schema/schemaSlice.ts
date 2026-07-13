import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import type { RootState } from "@/store/types";
import type { ImportedFile } from "@/types/importedFile";

export interface SchemaState {
	original: string;
	filtered: string;
	sourceFiles: ImportedFile[];
	includeBuiltDependencies: boolean;
}

const initialState: SchemaState = {
	original: "",
	filtered: "",
	sourceFiles: [],
	includeBuiltDependencies: false,
};

const schemaSlice = createSlice({
	name: "schema",
	initialState,
	reducers: {
		setOriginalSchema: (state, action: PayloadAction<string>) => {
			state.original = action.payload;
			state.filtered = action.payload;
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
export const selectFilteredSchema = (state: RootState) => state.schema.filtered;
export const selectSourceFiles = (state: RootState) => state.schema.sourceFiles;
export const selectIncludeBuiltDependencies = (state: RootState) =>
	state.schema.includeBuiltDependencies;

export default schemaSlice.reducer;
