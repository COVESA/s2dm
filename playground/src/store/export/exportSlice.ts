import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import type { RootState } from "@/store/types";

export interface ExportSchemaOptions {
	endpoint: string;
}

type ExportResult = {
	output: string;
	format: string;
};

export interface ExportState {
	isExporting: boolean;
	activeEndpoint: string | null;
	resultsByEndpoint: Record<string, ExportResult>;
	errorsByEndpoint: Record<string, string>;
}

const initialState: ExportState = {
	isExporting: false,
	activeEndpoint: null,
	resultsByEndpoint: {},
	errorsByEndpoint: {},
};

const exportSlice = createSlice({
	name: "schemaExport",
	initialState,
	reducers: {
		exportSchema: (state, action: PayloadAction<ExportSchemaOptions>) => {
			state.isExporting = true;
			state.activeEndpoint = action.payload.endpoint;
			delete state.errorsByEndpoint[action.payload.endpoint];
		},
		exportSuccess: (
			state,
			action: PayloadAction<{ endpoint: string; output: string; format: string }>,
		) => {
			state.isExporting = false;
			state.activeEndpoint = null;
			state.resultsByEndpoint[action.payload.endpoint] = {
				output: action.payload.output,
				format: action.payload.format,
			};
			delete state.errorsByEndpoint[action.payload.endpoint];
		},
		exportFailure: (
			state,
			action: PayloadAction<{ endpoint: string; error: string }>,
		) => {
			state.isExporting = false;
			state.activeEndpoint = null;
			state.errorsByEndpoint[action.payload.endpoint] = action.payload.error;
			delete state.resultsByEndpoint[action.payload.endpoint];
		},
		clearExportResult: (state) => {
			state.resultsByEndpoint = {};
			state.errorsByEndpoint = {};
		},
		clearExportResultForEndpoint: (state, action: PayloadAction<string>) => {
			delete state.resultsByEndpoint[action.payload];
			delete state.errorsByEndpoint[action.payload];
		},
	},
});

export const {
	exportSchema,
	exportSuccess,
	exportFailure,
	clearExportResult,
	clearExportResultForEndpoint,
} = exportSlice.actions;

export const selectIsExporting = (state: RootState) =>
	state.schemaExport.isExporting;
export const selectIsExportingEndpoint = (
	state: RootState,
	endpoint: string,
) =>
	state.schemaExport.isExporting && state.schemaExport.activeEndpoint === endpoint;
export const selectExportResult = (state: RootState, endpoint: string) =>
	state.schemaExport.resultsByEndpoint[endpoint]?.output || "";
export const selectExportFormat = (state: RootState, endpoint: string) =>
	state.schemaExport.resultsByEndpoint[endpoint]?.format || "text";
export const selectExportError = (state: RootState, endpoint: string) =>
	state.schemaExport.errorsByEndpoint[endpoint] || null;

export default exportSlice.reducer;
