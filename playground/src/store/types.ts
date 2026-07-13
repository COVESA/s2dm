import type { CapabilitiesState } from "@/store/capabilities/capabilitiesSlice";
import type { DepsComposeState } from "@/store/deps/compose/composeSlice";
import type { DependencyExplorationState } from "@/store/deps/dependencyExploration/dependencyExplorationSlice";
import type { DepsState } from "@/store/deps/depsSlice";
import type { DepsIdentitiesState } from "@/store/deps/identities/identitiesSlice";
import type { DepsResolveState } from "@/store/deps/resolve/resolveSlice";
import type { ExportState } from "@/store/export/exportSlice";
import type { SchemaState } from "@/store/schema/schemaSlice";
import type { SelectionState } from "@/store/selection/selectionSlice";
import type { UIState } from "@/store/ui/uiSlice";
import type { ValidationState } from "@/store/validation/validationSlice";

export interface RootState {
	deps: DepsState;
	dependencyExploration: DependencyExplorationState;
	depsIdentities: DepsIdentitiesState;
	depsResolve: DepsResolveState;
	depsCompose: DepsComposeState;
	schema: SchemaState;
	selection: SelectionState;
	validation: ValidationState;
	ui: UIState;
	schemaExport: ExportState;
	capabilities: CapabilitiesState;
}

export type {
	CapabilitiesState,
	DependencyExplorationState,
	DepsComposeState,
	DepsIdentitiesState,
	DepsResolveState,
	DepsState,
	ExportState,
	SchemaState,
	SelectionState,
	UIState,
	ValidationState,
};
