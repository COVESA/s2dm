import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import type { ExporterCapability, OpenAPISpec } from "@/api/types";
import type { RootState } from "@/store/types";

export interface CapabilitiesState {
	spec: OpenAPISpec | null;
	exporters: ExporterCapability[];
	isLoading: boolean;
	error: string | null;
}

const initialState: CapabilitiesState = {
	spec: null,
	exporters: [],
	isLoading: false,
	error: null,
};

const capabilitiesSlice = createSlice({
	name: "capabilities",
	initialState,
	reducers: {
		fetchCapabilities: (state) => {
			state.isLoading = true;
			state.error = null;
		},
		fetchCapabilitiesSuccess: (state, action: PayloadAction<OpenAPISpec>) => {
			state.spec = action.payload;
		},
		computeCapabilities: (state) => {
			state.isLoading = true;
			state.error = null;
		},
		computeCapabilitiesSuccess: (
			state,
			action: PayloadAction<ExporterCapability[]>,
		) => {
			state.isLoading = false;
			state.exporters = action.payload;
			state.error = null;
		},
		fetchCapabilitiesFailure: (state, action: PayloadAction<string>) => {
			state.isLoading = false;
			state.error = action.payload;
		},
		updatePropertyValue: (
			state,
			action: PayloadAction<{
				exporterName: string;
				propertyKey: string;
				value: unknown;
			}>,
		) => {
			const exporter = state.exporters.find(
				(exp) => exp.name === action.payload.exporterName,
			);
			if (!exporter) {
				return;
			}
			exporter.propertyValues[action.payload.propertyKey] =
				action.payload.value;
		},
	},
});

export const {
	fetchCapabilities,
	fetchCapabilitiesSuccess,
	fetchCapabilitiesFailure,
	computeCapabilities,
	computeCapabilitiesSuccess,
	updatePropertyValue,
} = capabilitiesSlice.actions;

export const selectCapabilitiesSpec = (state: RootState) =>
	state.capabilities.spec;
export const selectExporters = (state: RootState) =>
	state.capabilities.exporters;
export const selectIsLoadingCapabilities = (state: RootState) =>
	state.capabilities.isLoading;
export const selectCapabilitiesError = (state: RootState) =>
	state.capabilities.error;
export const selectExporterByName = (state: RootState, name: string) =>
	state.capabilities.exporters.find((exp) => exp.name === name);

export default capabilitiesSlice.reducer;
