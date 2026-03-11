import type { PayloadAction } from "@reduxjs/toolkit";
import { createSlice } from "@reduxjs/toolkit";
import type { ExporterCapability, OpenAPISpec } from "@/api/types";
import type { RootState } from "@/store/types";

export interface CapabilitiesState {
	spec: OpenAPISpec | null;
	exporters: ExporterCapability[];
	selectedExporterEndpoint: string;
	isLoading: boolean;
	error: string | null;
}

const initialState: CapabilitiesState = {
	spec: null,
	exporters: [],
	selectedExporterEndpoint: "",
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
			const selectedExporterStillExists = action.payload.some(
				(exporter) => exporter.endpoint === state.selectedExporterEndpoint,
			);
			if (!selectedExporterStillExists) {
				state.selectedExporterEndpoint = action.payload[0]?.endpoint || "";
			}
			state.error = null;
		},
		fetchCapabilitiesFailure: (state, action: PayloadAction<string>) => {
			state.isLoading = false;
			state.error = action.payload;
		},
		updatePropertyValue: (
			state,
			action: PayloadAction<{
				exporterEndpoint: string;
				propertyKey: string;
				value: unknown;
			}>,
		) => {
			const exporter = state.exporters.find(
				(exp) => exp.endpoint === action.payload.exporterEndpoint,
			);
			if (!exporter) {
				return;
			}
			exporter.propertyValues[action.payload.propertyKey] =
				action.payload.value;
		},
		setSelectedExporterEndpoint: (state, action: PayloadAction<string>) => {
			state.selectedExporterEndpoint = action.payload;
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
	setSelectedExporterEndpoint,
} = capabilitiesSlice.actions;

export const selectCapabilitiesSpec = (state: RootState) =>
	state.capabilities.spec;
export const selectExporters = (state: RootState) =>
	state.capabilities.exporters;
export const selectIsLoadingCapabilities = (state: RootState) =>
	state.capabilities.isLoading;
export const selectCapabilitiesError = (state: RootState) =>
	state.capabilities.error;
export const selectExporterByEndpoint = (state: RootState, endpoint: string) =>
	state.capabilities.exporters.find((exp) => exp.endpoint === endpoint);
export const selectSelectedExporterEndpoint = (state: RootState) =>
	state.capabilities.selectedExporterEndpoint;

export default capabilitiesSlice.reducer;
