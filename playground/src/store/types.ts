import type { CapabilitiesState } from "@/store/capabilities/capabilitiesSlice";
import type { ExportState } from "@/store/export/exportSlice";
import type { SchemaState } from "@/store/schema/schemaSlice";
import type { SelectionState } from "@/store/selection/selectionSlice";
import type { UIState } from "@/store/ui/uiSlice";
import type { ValidationState } from "@/store/validation/validationSlice";

export interface RootState {
	schema: SchemaState;
	selection: SelectionState;
	validation: ValidationState;
	ui: UIState;
	schemaExport: ExportState;
	capabilities: CapabilitiesState;
}

export type {
	SchemaState,
	SelectionState,
	ValidationState,
	UIState,
	ExportState,
	CapabilitiesState,
};
