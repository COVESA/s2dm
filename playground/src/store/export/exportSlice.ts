import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import type { RootState } from "@/store/types";

export interface ExportSchemaOptions {
	endpoint: string;
}

export interface ExportState {
	isExporting: boolean;
	result: { output: string; format: string } | null;
	error: string | null;
}

const initialState: ExportState = {
	isExporting: false,
	result: null,
	error: null,
};

const exportSlice = createSlice({
	name: "schemaExport",
	initialState,
	reducers: {
		exportSchema: (state, _action: PayloadAction<ExportSchemaOptions>) => {
			state.isExporting = true;
			state.error = null;
		},
		exportSuccess: (
			state,
			action: PayloadAction<{ output: string; format: string }>,
		) => {
			state.isExporting = false;
			state.result = action.payload;
			state.error = null;
		},
		exportFailure: (state, action: PayloadAction<string>) => {
			state.isExporting = false;
			state.error = action.payload;
			state.result = null;
		},
		clearExportResult: (state) => {
			state.result = null;
			state.error = null;
		},
	},
});

export const { exportSchema, exportSuccess, exportFailure, clearExportResult } =
	exportSlice.actions;

export const selectIsExporting = (state: RootState) =>
	state.schemaExport.isExporting;
export const selectExportResult = (state: RootState) =>
	state.schemaExport.result?.output || "";
export const selectExportFormat = (state: RootState) =>
	state.schemaExport.result?.format || "text";
export const selectExportError = (state: RootState) => state.schemaExport.error;

export default exportSlice.reducer;
