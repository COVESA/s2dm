import { PREDEFINED_QUERIES } from "@ledger-ui/data/predefinedQueries";
import { DEFAULT_SEARCH_OPTIONS } from "@ledger-ui/data/search";
import type { LedgerSearchMatch } from "@ledger-ui/data/types";
import ledgerDetailReducer from "@ledger-ui/state/ledgerDetailSlice";
import ledgerExploreReducer from "@ledger-ui/state/ledgerExploreSlice";
import ledgerFileReducer from "@ledger-ui/state/ledgerFileSlice";
import ledgerQueryReducer from "@ledger-ui/state/ledgerQuerySlice";
import {
	applyPredefinedQuery,
	chooseLedgerTable,
	exploreLedgerSuccess,
	type LedgerDetail,
	openLedger,
	openLedgerDetail,
	openLedgerFailure,
	openLedgerSuccess,
	popLedgerDetail,
	pushLedgerDetail,
	selectCanGoBackLedgerDetail,
	selectLedgerDetail,
	selectLedgerStatus,
	setExploreQuery,
	setLedgerFilter,
	setLedgerPage,
	setLedgerSearch,
	setLedgerSql,
	setLedgerView,
	setSearchOptions,
	showRecordInTable,
} from "@ledger-ui/state/ledgerSlice";
import ledgerTableReducer from "@ledger-ui/state/ledgerTableSlice";
import type { LedgerRootState } from "@ledger-ui/state/types";
import { describe, expect, it } from "vitest";
import { column, ledgerTable } from "./fixtures";

const INIT_ACTION = { type: "test/init" };

const KEY_COLUMNS = [column("serial", 1)];

const TABLES = [
	ledgerTable("concepts", KEY_COLUMNS),
	ledgerTable("revisions", KEY_COLUMNS),
];

const OPENED = openLedgerSuccess({ fileName: "ledger.db", tables: TABLES });

const FAILED_IMPORT = openLedgerFailure({ message: "unreadable" });

const CONCEPT_DETAIL: LedgerDetail = {
	kind: "row",
	table: "concepts",
	record: { serial: 0 },
};

const REVISION_DETAIL: LedgerDetail = {
	kind: "row",
	table: "revisions",
	record: { serial: 0 },
};

function rootState(overrides: Partial<LedgerRootState> = {}): LedgerRootState {
	const initialFile = ledgerFileReducer(undefined, INIT_ACTION);
	const initialTable = ledgerTableReducer(undefined, INIT_ACTION);
	const initialExplore = ledgerExploreReducer(undefined, INIT_ACTION);
	const initialQuery = ledgerQueryReducer(undefined, INIT_ACTION);
	const initialDetail = ledgerDetailReducer(undefined, INIT_ACTION);
	const initialState: LedgerRootState = {
		ledgerFile: initialFile,
		ledgerTable: initialTable,
		ledgerExplore: initialExplore,
		ledgerQuery: initialQuery,
		ledgerDetail: initialDetail,
	};
	return { ...initialState, ...overrides };
}

describe("ledgerFile reducer", () => {
	it("keeps the ledger after a failed import", () => {
		const opened = ledgerFileReducer(undefined, OPENED);

		const state = ledgerFileReducer(opened, FAILED_IMPORT);

		expect(state.tables).toEqual(TABLES);
		expect(state.fileName).toBe("ledger.db");
	});

	it("merges new search options into the current ones", () => {
		const action = setSearchOptions({ regex: true });

		const state = ledgerFileReducer(undefined, action);

		expect(state.searchOptions).toEqual({
			...DEFAULT_SEARCH_OPTIONS,
			regex: true,
		});
	});

	it("switches to the raw view to show a record", () => {
		const queryViewAction = setLedgerView("query");
		const queryView = ledgerFileReducer(undefined, queryViewAction);
		const action = showRecordInTable({ table: "concepts", record: {} });

		const state = ledgerFileReducer(queryView, action);

		expect(state.view).toBe("raw");
	});
});

describe("selectLedgerStatus", () => {
	it("is idle before a ledger opens", () => {
		const state = rootState();

		const status = selectLedgerStatus(state);

		expect(status).toBe("idle");
	});

	it("is loading while a ledger opens", () => {
		const bytes = new Uint8Array();
		const action = openLedger({ name: "ledger.db", bytes });
		const ledgerFile = ledgerFileReducer(undefined, action);
		const state = rootState({ ledgerFile });

		const status = selectLedgerStatus(state);

		expect(status).toBe("loading");
	});

	it("is ready when the ledger has tables", () => {
		const ledgerFile = ledgerFileReducer(undefined, OPENED);
		const state = rootState({ ledgerFile });

		const status = selectLedgerStatus(state);

		expect(status).toBe("ready");
	});

	it("is empty when the ledger has no tables", () => {
		const action = openLedgerSuccess({ fileName: "ledger.db", tables: [] });
		const ledgerFile = ledgerFileReducer(undefined, action);
		const state = rootState({ ledgerFile });

		const status = selectLedgerStatus(state);

		expect(status).toBe("empty");
	});

	it("is ready while a new import runs over a loaded ledger", () => {
		const bytes = new Uint8Array();
		const importAction = openLedger({ name: "other.db", bytes });
		const opened = ledgerFileReducer(undefined, OPENED);
		const ledgerFile = ledgerFileReducer(opened, importAction);
		const state = rootState({ ledgerFile });

		const status = selectLedgerStatus(state);

		expect(status).toBe("ready");
	});

	it("is ready after a failed import leaves the ledger on screen", () => {
		const opened = ledgerFileReducer(undefined, OPENED);
		const ledgerFile = ledgerFileReducer(opened, FAILED_IMPORT);
		const state = rootState({ ledgerFile });

		const status = selectLedgerStatus(state);

		expect(status).toBe("ready");
	});

	it("is failed when an import fails with no ledger on screen", () => {
		const ledgerFile = ledgerFileReducer(undefined, FAILED_IMPORT);
		const state = rootState({ ledgerFile });

		const status = selectLedgerStatus(state);

		expect(status).toBe("failed");
	});
});

describe("ledgerTable reducer", () => {
	it("selects the first table when a ledger opens", () => {
		const state = ledgerTableReducer(undefined, OPENED);

		expect(state.selectedTable).toBe("concepts");
	});

	it("removes a filter set to an empty value", () => {
		const setFilter = setLedgerFilter({ column: "status", value: "ACTIVE" });
		const clearFilter = setLedgerFilter({ column: "status", value: "" });
		const filtered = ledgerTableReducer(undefined, setFilter);

		const state = ledgerTableReducer(filtered, clearFilter);

		expect(state.filters).toEqual({});
	});

	it("goes back to the first page when a filter changes", () => {
		const pageAction = setLedgerPage(3);
		const paged = ledgerTableReducer(undefined, pageAction);
		const action = setLedgerFilter({ column: "status", value: "ACTIVE" });

		const state = ledgerTableReducer(paged, action);

		expect(state.page).toBe(0);
	});

	it("does not go below the first page", () => {
		const pageAction = setLedgerPage(-2);

		const state = ledgerTableReducer(undefined, pageAction);

		expect(state.page).toBe(0);
	});

	it("keeps the page on new search options when there is no search", () => {
		const pageAction = setLedgerPage(3);
		const paged = ledgerTableReducer(undefined, pageAction);
		const action = setSearchOptions({ regex: true });

		const state = ledgerTableReducer(paged, action);

		expect(state.page).toBe(3);
	});

	it("goes back to the first page on new search options during a search", () => {
		const searchAction = setLedgerSearch("car");
		const pageAction = setLedgerPage(3);
		const searched = ledgerTableReducer(undefined, searchAction);
		const paged = ledgerTableReducer(searched, pageAction);
		const action = setSearchOptions({ regex: true });

		const state = ledgerTableReducer(paged, action);

		expect(state.page).toBe(0);
	});

	it("keeps the page and clears the search to show a record", () => {
		const searchAction = setLedgerSearch("car");
		const pageAction = setLedgerPage(3);
		const searched = ledgerTableReducer(undefined, searchAction);
		const paged = ledgerTableReducer(searched, pageAction);
		const action = showRecordInTable({ table: "revisions", record: {} });

		const state = ledgerTableReducer(paged, action);

		expect(state.page).toBe(3);
		expect(state.search).toBe("");
		expect(state.selectedTable).toBe("revisions");
	});

	it("keeps the table after a failed import", () => {
		const chooseAction = chooseLedgerTable("revisions");
		const chosen = ledgerTableReducer(undefined, chooseAction);

		const state = ledgerTableReducer(chosen, FAILED_IMPORT);

		expect(state.selectedTable).toBe("revisions");
	});
});

describe("ledgerDetail reducer", () => {
	it("goes back to the previous detail", () => {
		const openAction = openLedgerDetail(CONCEPT_DETAIL);
		const opened = ledgerDetailReducer(undefined, openAction);
		const pushAction = pushLedgerDetail(REVISION_DETAIL);
		const pushed = ledgerDetailReducer(opened, pushAction);
		const pushedState = rootState({ ledgerDetail: pushed });

		const popAction = popLedgerDetail();
		const popped = ledgerDetailReducer(pushed, popAction);
		const poppedState = rootState({ ledgerDetail: popped });

		const pushedDetail = selectLedgerDetail(pushedState);
		const canGoBackFromPushed = selectCanGoBackLedgerDetail(pushedState);
		const poppedDetail = selectLedgerDetail(poppedState);
		const canGoBackFromPopped = selectCanGoBackLedgerDetail(poppedState);
		expect(pushedDetail).toEqual(REVISION_DETAIL);
		expect(canGoBackFromPushed).toBe(true);
		expect(poppedDetail).toEqual(CONCEPT_DETAIL);
		expect(canGoBackFromPopped).toBe(false);
	});

	it("stops loading the chain when the last detail closes", () => {
		const openAction = openLedgerDetail(CONCEPT_DETAIL);
		const opened = ledgerDetailReducer(undefined, openAction);
		const popAction = popLedgerDetail();

		const state = ledgerDetailReducer(opened, popAction);

		expect(state.isLoadingChain).toBe(false);
	});

	it("clears the details when a new ledger opens", () => {
		const openAction = openLedgerDetail(CONCEPT_DETAIL);
		const opened = ledgerDetailReducer(undefined, openAction);

		const state = ledgerDetailReducer(opened, OPENED);

		expect(state.detailStack).toEqual([]);
	});
});

describe("ledgerExplore reducer", () => {
	it("clears the matches when the query becomes blank", () => {
		const match: LedgerSearchMatch = {
			table: "concepts",
			result: { columns: [], rows: [], truncated: false },
			total: 0,
		};
		const successAction = exploreLedgerSuccess([match]);
		const blankQueryAction = setExploreQuery("   ");
		const explored = ledgerExploreReducer(undefined, successAction);

		const state = ledgerExploreReducer(explored, blankQueryAction);

		expect(state.exploreMatches).toEqual([]);
		expect(state.hasExplored).toBe(false);
		expect(state.isExploring).toBe(false);
	});

	it("starts exploring from the first keystroke", () => {
		const queryAction = setExploreQuery("car");

		const state = ledgerExploreReducer(undefined, queryAction);

		expect(state.isExploring).toBe(true);
	});
});

describe("ledgerQuery reducer", () => {
	const predefinedQuery = PREDEFINED_QUERIES[1];

	it("applies a predefined query", () => {
		const action = applyPredefinedQuery(predefinedQuery?.label ?? "");

		const state = ledgerQueryReducer(undefined, action);

		expect(state.sql).toBe(predefinedQuery?.sql);
		expect(state.predefinedQuery).toBe(predefinedQuery?.label);
	});

	it("forgets the predefined query when the SQL changes", () => {
		const action = applyPredefinedQuery(predefinedQuery?.label ?? "");
		const applied = ledgerQueryReducer(undefined, action);
		const sqlAction = setLedgerSql("SELECT 1");

		const state = ledgerQueryReducer(applied, sqlAction);

		expect(state.predefinedQuery).toBe("");
	});

	it("ignores an unknown predefined query", () => {
		const initialState = ledgerQueryReducer(undefined, INIT_ACTION);
		const unknownAction = applyPredefinedQuery("unknown");

		const state = ledgerQueryReducer(initialState, unknownAction);

		expect(state).toEqual(initialState);
	});
});
