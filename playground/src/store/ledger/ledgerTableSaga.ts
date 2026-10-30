import { call, debounce, put, select, takeLatest } from "redux-saga/effects";
import { FILTERABLE_COLUMNS } from "@/ledger/modlProfile";
import {
	countSearchMatches,
	LEDGER_PAGE_SIZE,
	listDistinctValues,
	searchTable,
} from "@/ledger/rows";
import type { SearchOptions } from "@/ledger/search";
import { getLedgerDatabase } from "@/ledger/session";
import type { QueryResult } from "@/ledger/types";
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
} from "@/store/ledger/ledgerSlice";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* loadFilterOptionsWorker() {
	try {
		const table: string = yield select(selectSelectedLedgerTable);
		if (!table) {
			return;
		}
		const database = getLedgerDatabase();
		const options: Record<string, string[]> = {};
		for (const column of FILTERABLE_COLUMNS) {
			const values: string[] = yield call(
				listDistinctValues,
				database,
				table,
				column,
			);
			if (values.length > 0) {
				options[column] = values;
			}
		}
		yield put(setLedgerFilterOptions(options));
	} catch {
		// The dropdowns are an aid, so a failure here leaves the rows alone.
	}
}

function* loadLedgerRowsWorker() {
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
		const database = getLedgerDatabase();
		const search: SearchOptions = yield select(selectSearchOptions);
		const window = {
			limit: LEDGER_PAGE_SIZE,
			offset: page * LEDGER_PAGE_SIZE,
			filters,
			search,
		};

		// An empty needle contributes no clause, so one call covers both cases.
		const result: QueryResult = yield call(
			searchTable,
			database,
			table,
			trimmed,
			window,
		);
		// Filters must reach the count, or the page numbers describe the whole table.
		const total: number = yield call(
			countSearchMatches,
			database,
			table,
			trimmed,
			{ filters, search },
		);

		yield put(loadLedgerRowsSuccess({ result, total }));
	} catch (error) {
		const message = getErrorMessage(error);
		yield put(loadLedgerRowsFailure(message));
	}
}

export function* ledgerTableSaga() {
	yield takeLatest(chooseLedgerTable.type, loadLedgerRowsWorker);
	yield takeLatest(loadLedgerRows.type, loadLedgerRowsWorker);
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
	yield takeLatest(setLedgerPage.type, loadLedgerRowsWorker);
	yield takeLatest(setLedgerFilter.type, loadLedgerRowsWorker);
	yield takeLatest(setSearchOptions.type, loadLedgerRowsWorker);
	yield takeLatest(openTableWithSearch.type, loadLedgerRowsWorker);
	yield debounce(200, setLedgerSearch.type, loadLedgerRowsWorker);
}
