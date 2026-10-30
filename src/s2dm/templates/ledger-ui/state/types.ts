import type { LedgerDetailState } from "@ledger-ui/state/ledgerDetailSlice";
import type { LedgerExploreState } from "@ledger-ui/state/ledgerExploreSlice";
import type { LedgerFileState } from "@ledger-ui/state/ledgerFileSlice";
import type { LedgerQueryState } from "@ledger-ui/state/ledgerQuerySlice";
import type { LedgerTableState } from "@ledger-ui/state/ledgerTableSlice";

/**
 * The store shape the shared ledger selectors and components read from.
 *
 * Each host declares its own, larger `RootState`. Because that shape structurally
 * satisfies this one, host-typed hooks accept the shared selectors and vice versa.
 */
export type LedgerRootState = {
	ledgerFile: LedgerFileState;
	ledgerTable: LedgerTableState;
	ledgerExplore: LedgerExploreState;
	ledgerQuery: LedgerQueryState;
	ledgerDetail: LedgerDetailState;
};
