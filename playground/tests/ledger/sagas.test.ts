import type { LedgerSearchMatch, QueryResult } from "@ledger-ui/data/types";
import ledgerDetailReducer from "@ledger-ui/state/ledgerDetailSlice";
import { ledgerExploreSaga } from "@ledger-ui/state/ledgerExploreSaga";
import ledgerExploreReducer from "@ledger-ui/state/ledgerExploreSlice";
import ledgerFileReducer from "@ledger-ui/state/ledgerFileSlice";
import ledgerQueryReducer from "@ledger-ui/state/ledgerQuerySlice";
import {
	chooseLedgerTable,
	exploreLedgerSuccess,
	loadLedgerRowsSuccess,
	openLedgerSuccess,
	setExploreQuery,
	setLedgerPage,
} from "@ledger-ui/state/ledgerSlice";
import { ledgerTableSaga } from "@ledger-ui/state/ledgerTableSaga";
import ledgerTableReducer from "@ledger-ui/state/ledgerTableSlice";
import { configureStore, type Middleware } from "@reduxjs/toolkit";
import createSagaMiddleware, { type Saga } from "redux-saga";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { column, ledgerTable } from "./fixtures";

const fakeLedger = vi.hoisted(() => {
	const searchAnswers: Array<(result: unknown) => void> = [];

	/**
	 * Stands in for the ledger worker. It answers a count or a list of filter
	 * values at once, and holds each search until the test answers it.
	 *
	 * @param operation - The ledger operation that the saga calls.
	 * @returns The operation's result, which for a search settles only when the
	 * test answers it.
	 */
	function callLedger(operation: string): Promise<unknown> {
		if (operation === "countSearchMatches") {
			return Promise.resolve(0);
		}
		if (operation === "listDistinctValues") {
			return Promise.resolve([]);
		}
		return new Promise((answer) => {
			searchAnswers.push(answer);
		});
	}

	return { searchAnswers, callLedger };
});

vi.mock("@ledger-ui/data/ledgerClient", () => ({
	callLedger: fakeLedger.callLedger,
}));

const KEY_COLUMNS = [column("serial", 1)];

const TABLES = [
	ledgerTable("concepts", KEY_COLUMNS),
	ledgerTable("revisions", KEY_COLUMNS),
];

const OPENED = openLedgerSuccess({ fileName: "ledger.db", tables: TABLES });

const CONCEPT_ROWS: QueryResult = {
	columns: ["serial"],
	rows: [[1]],
	truncated: false,
};

const REVISION_ROWS: QueryResult = {
	columns: ["serial"],
	rows: [[2]],
	truncated: false,
};

const SPEED_MATCH: LedgerSearchMatch = {
	table: "concepts",
	result: CONCEPT_ROWS,
	total: 1,
};

const SPEEDO_MATCH: LedgerSearchMatch = {
	table: "revisions",
	result: REVISION_ROWS,
	total: 1,
};

function startLedgerSaga(saga: Saga) {
	const dispatched: unknown[] = [];
	const recordAction: Middleware = () => (next) => (action) => {
		dispatched.push(action);
		return next(action);
	};
	const sagaMiddleware = createSagaMiddleware();
	const store = configureStore({
		reducer: {
			ledgerFile: ledgerFileReducer,
			ledgerTable: ledgerTableReducer,
			ledgerExplore: ledgerExploreReducer,
			ledgerQuery: ledgerQueryReducer,
			ledgerDetail: ledgerDetailReducer,
		},
		middleware: (getDefaultMiddleware) =>
			getDefaultMiddleware().concat(recordAction, sagaMiddleware),
	});
	sagaMiddleware.run(saga);
	return { store, dispatched };
}

beforeEach(() => {
	vi.useFakeTimers();
});

afterEach(() => {
	fakeLedger.searchAnswers.length = 0;
	vi.useRealTimers();
});

describe("ledgerTableSaga", () => {
	it("drops a row load that a newer change replaced", async () => {
		const { store, dispatched } = startLedgerSaga(ledgerTableSaga);
		const pageAction = setLedgerPage(1);
		const chooseAction = chooseLedgerTable("revisions");
		store.dispatch(OPENED);

		store.dispatch(pageAction);
		store.dispatch(chooseAction);
		const [answerConceptPage, answerRevisions] = fakeLedger.searchAnswers;
		answerConceptPage(CONCEPT_ROWS);
		answerRevisions(REVISION_ROWS);
		await vi.runAllTimersAsync();

		const loadedResults = dispatched
			.filter(loadLedgerRowsSuccess.match)
			.map((action) => action.payload.result);
		expect(loadedResults).toEqual([REVISION_ROWS]);
	});
});

describe("ledgerExploreSaga", () => {
	it("drops a search that a newer keystroke replaced", async () => {
		const { store, dispatched } = startLedgerSaga(ledgerExploreSaga);
		const firstQuery = setExploreQuery("speed");
		const secondQuery = setExploreQuery("speedo");

		store.dispatch(firstQuery);
		await vi.runAllTimersAsync();
		store.dispatch(secondQuery);
		await vi.runAllTimersAsync();
		const [answerFirstSearch, answerSecondSearch] = fakeLedger.searchAnswers;
		answerFirstSearch([SPEED_MATCH]);
		answerSecondSearch([SPEEDO_MATCH]);
		await vi.runAllTimersAsync();

		const exploredMatches = dispatched
			.filter(exploreLedgerSuccess.match)
			.map((action) => action.payload);
		expect(exploredMatches).toEqual([[SPEEDO_MATCH]]);
	});
});
