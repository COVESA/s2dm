import { callLedger } from "@ledger-ui/data/ledgerClient";
import { FILTERABLE_COLUMNS } from "@ledger-ui/data/modlProfile";
import { LEDGER_PAGE_SIZE } from "@ledger-ui/data/rows";
import type { SearchOptions } from "@ledger-ui/data/search";
import type { QueryResult } from "@ledger-ui/data/types";
import {
	chooseLedgerTable,
	loadLedgerRows,
	loadLedgerRowsFailure,
	loadLedgerRowsSuccess,
	openTableWithSearch,
	selectLedgerFilters,
	selectLedgerPage,
	selectLedgerSearch,
	selectSearchOptions,
	selectSelectedLedgerTable,
	setLedgerFilter,
	setLedgerFilterOptions,
	setLedgerPage,
	setLedgerSearch,
	setSearchOptions,
	showRecordInTable,
} from "@ledger-ui/state/ledgerSlice";
import type { UnknownAction } from "@reduxjs/toolkit";
import { call, delay, put, select, takeLatest } from "redux-saga/effects";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* loadFilterOptionsWorker() {
	try {
		const table: string = yield select(selectSelectedLedgerTable);
		if (!table) {
			return;
		}
		const options: Record<string, string[]> = {};
		for (const column of FILTERABLE_COLUMNS) {
			const values: string[] = yield call(callLedger, "listDistinctValues", {
				table,
				column,
			});
			if (values.length > 0) {
				options[column] = values;
			}
		}
		yield put(setLedgerFilterOptions(options));
	} catch {
		// The dropdowns are an aid, so a failure here leaves the rows alone.
	}
}

function* loadLedgerRowsWorker(action: UnknownAction) {
	// A keystroke waits for a pause in typing. A newer action cancels the wait.
	if (setLedgerSearch.match(action)) {
		yield delay(SEARCH_DEBOUNCE_MS);
	}
	try {
		const table: string = yield select(selectSelectedLedgerTable);
		if (!table) {
			yield put(
				loadLedgerRowsSuccess({
					result: { columns: [], rows: [], truncated: false },
					total: 0,
				}),
			);
			return;
		}

		const needle: string = yield select(selectLedgerSearch);
		const page: number = yield select(selectLedgerPage);
		const filters: Record<string, string> = yield select(selectLedgerFilters);
		const trimmed = needle.trim();
		const search: SearchOptions = yield select(selectSearchOptions);

		// An empty needle contributes no clause, so one call covers both cases.
		const result: QueryResult = yield call(callLedger, "searchTable", {
			table,
			needle: trimmed,
			limit: LEDGER_PAGE_SIZE,
			offset: page * LEDGER_PAGE_SIZE,
			filters,
			search,
		});
		// Filters must reach the count, or the page numbers describe the whole table.
		const total: number = yield call(callLedger, "countSearchMatches", {
			table,
			needle: trimmed,
			filters,
			search,
		});

		yield put(loadLedgerRowsSuccess({ result, total }));
	} catch (error) {
		const message = getErrorMessage(error);
		yield put(loadLedgerRowsFailure(message));
	}
}

// The pause in typing before a table search runs.
const SEARCH_DEBOUNCE_MS = 200;

export function* ledgerTableSaga() {
	// One watcher for every change that reloads the rows, so a newer change
	// cancels the load still running.
	yield takeLatest(
		[
			chooseLedgerTable.type,
			loadLedgerRows.type,
			setLedgerPage.type,
			setLedgerFilter.type,
			setLedgerSearch.type,
			setSearchOptions.type,
			openTableWithSearch.type,
		],
		loadLedgerRowsWorker,
	);
	// Only where the table itself changes: the values do not depend on the page,
	// the needle or the filters.
	yield takeLatest(
		[
			chooseLedgerTable.type,
			loadLedgerRows.type,
			openTableWithSearch.type,
			showRecordInTable.type,
		],
		loadFilterOptionsWorker,
	);
}
