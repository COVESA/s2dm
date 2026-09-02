import type { InsightDetailState } from "@insights-ui/state/insightDetailSlice";
import type { InsightsState } from "@insights-ui/state/insightsSlice";
import type { CapabilitiesState } from "@/store/capabilities/capabilitiesSlice";
import type { DepsComposeState } from "@/store/deps/compose/composeSlice";
import type { DependencyExplorationState } from "@/store/deps/dependencyExploration/dependencyExplorationSlice";
import type { DepsState } from "@/store/deps/depsSlice";
import type { DepsIdentitiesState } from "@/store/deps/identities/identitiesSlice";
import type { DepsResolveState } from "@/store/deps/resolve/resolveSlice";
import type { ExportState } from "@/store/export/exportSlice";
import type { LedgerDetailState } from "@/store/ledger/ledgerDetailSlice";
import type { LedgerExploreState } from "@/store/ledger/ledgerExploreSlice";
import type { LedgerFileState } from "@/store/ledger/ledgerFileSlice";
import type { LedgerQueryState } from "@/store/ledger/ledgerQuerySlice";
import type { LedgerTableState } from "@/store/ledger/ledgerTableSlice";
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
	ledgerFile: LedgerFileState;
	ledgerTable: LedgerTableState;
	ledgerExplore: LedgerExploreState;
	ledgerQuery: LedgerQueryState;
	ledgerDetail: LedgerDetailState;
	selection: SelectionState;
	validation: ValidationState;
	ui: UIState;
	schemaExport: ExportState;
	capabilities: CapabilitiesState;
	insights: InsightsState;
	insightDetail: InsightDetailState;
}
