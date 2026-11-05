import { callLedger } from "@ledger-ui/data/ledgerClient";
import type { SearchOptions } from "@ledger-ui/data/search";
import type { LedgerSearchMatch } from "@ledger-ui/data/types";
import {
	exploreLedger,
	exploreLedgerFailure,
	exploreLedgerSuccess,
	selectExploreQuery,
	selectSearchOptions,
	setExploreQuery,
	setSearchOptions,
} from "@ledger-ui/state/ledgerSlice";
import type { UnknownAction } from "@reduxjs/toolkit";
import { call, delay, put, select, takeLatest } from "redux-saga/effects";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* exploreLedgerWorker(action: UnknownAction) {
	// A keystroke waits for a pause in typing. A newer action cancels the wait.
	if (setExploreQuery.match(action)) {
		yield delay(EXPLORE_DEBOUNCE_MS);
	}
	try {
		const exploreNeedle: string = yield select(selectExploreQuery);
		const trimmed = exploreNeedle.trim();
		if (!trimmed) {
			return;
		}

		const search: SearchOptions = yield select(selectSearchOptions);
		yield put(exploreLedger());
		const matches: LedgerSearchMatch[] = yield call(
			callLedger,
			"searchLedger",
			{
				needle: trimmed,
				limit: EXPLORE_PREVIEW_LIMIT,
				search,
			},
		);
		yield put(exploreLedgerSuccess(matches));
	} catch (error) {
		const message = getErrorMessage(error);
		yield put(exploreLedgerFailure(message));
	}
}

// Rows previewed per matching table; "Display all" opens the full table.
const EXPLORE_PREVIEW_LIMIT = 5;

// The pause in typing before a search runs.
const EXPLORE_DEBOUNCE_MS = 250;

export function* ledgerExploreSaga() {
	// One watcher, so a newer keystroke or option cancels the search still running.
	yield takeLatest(
		[setExploreQuery.type, setSearchOptions.type],
		exploreLedgerWorker,
	);
}
