import { call, debounce, put, select, takeLatest } from "redux-saga/effects";
import { searchLedger } from "@/ledger/ledgerSearch";
import type { SearchOptions } from "@/ledger/search";
import { getLedgerDatabase } from "@/ledger/session";
import type { LedgerSearchMatch, LedgerTable } from "@/ledger/types";
import {
	exploreLedger,
	exploreLedgerFailure,
	exploreLedgerSuccess,
	selectExploreQuery,
	selectLedgerTables,
	selectSearchOptions,
	setExploreQuery,
	setSearchOptions,
} from "@/store/ledger/ledgerSlice";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* exploreLedgerWorker() {
	try {
		const exploreNeedle: string = yield select(selectExploreQuery);
		const trimmed = exploreNeedle.trim();
		if (!trimmed) {
			return;
		}

		const search: SearchOptions = yield select(selectSearchOptions);
		yield put(exploreLedger());
		const database = getLedgerDatabase();
		const tables: LedgerTable[] = yield select(selectLedgerTables);
		const matches: LedgerSearchMatch[] = yield call(
			searchLedger,
			database,
			tables,
			trimmed,
			{ limit: EXPLORE_PREVIEW_LIMIT, search },
		);
		yield put(exploreLedgerSuccess(matches));
	} catch (error) {
		const message = getErrorMessage(error);
		yield put(exploreLedgerFailure(message));
	}
}

// Rows previewed per matching table; "Display all" opens the full table.
const EXPLORE_PREVIEW_LIMIT = 5;

export function* ledgerExploreSaga() {
	yield takeLatest(setSearchOptions.type, exploreLedgerWorker);
	yield debounce(250, setExploreQuery.type, exploreLedgerWorker);
}
