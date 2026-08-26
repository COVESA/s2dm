import type { PayloadAction } from "@reduxjs/toolkit";
import { call, debounce, put, select, takeLatest } from "redux-saga/effects";
import type { Database } from "sql.js";
import { type LedgerChain, resolveChain } from "@/ledger/chain";
import {
	EXPLORE_PREVIEW_LIMIT,
	FILTERABLE_COLUMNS,
	LEDGER_PAGE_SIZE,
} from "@/ledger/constants";
import {
	countRows,
	countSearchMatches,
	findRows,
	listDistinctValues,
	readSchema,
	readTablePage,
	rowPageIndex,
	runReadQuery,
	searchLedger,
	searchTable,
	toRecords,
} from "@/ledger/introspect";
import { matchSingleRecordTable } from "@/ledger/resultRecord";
import type { SearchOptions } from "@/ledger/search";
import {
	beginLedgerOpen,
	closeLedgerDatabase,
	getLedgerDatabase,
	setLedgerDatabase,
} from "@/ledger/session";
import {
	LedgerImportSuperseded,
	openLedgerDatabase,
	readFileBytes,
} from "@/ledger/sqlite";
import type {
	LedgerRecord,
	LedgerSearchMatch,
	LedgerTable,
	QueryResult,
} from "@/ledger/types";
import {
	closeLedger,
	exploreLedger,
	exploreLedgerFailure,
	exploreLedgerSuccess,
	type LedgerDetail,
	loadLedgerRows,
	loadLedgerRowsFailure,
	loadLedgerRowsSuccess,
	openLedger,
	openLedgerDetail,
	openLedgerFailure,
	openLedgerSuccess,
	openTableWithSearch,
	popLedgerDetail,
	pushLedgerDetail,
	resolveChainFailure,
	resolveChainSuccess,
	runLedgerQuery,
	runLedgerQueryFailure,
	runLedgerQuerySuccess,
	selectExploreQuery,
	selectLedgerDetail,
	selectLedgerFilters,
	selectLedgerPage,
	selectLedgerSearch,
	selectLedgerSql,
	selectLedgerTable,
	selectLedgerTables,
	selectSearchOptions,
	selectSelectedLedgerTable,
	setExploreQuery,
	setLedgerFilter,
	setLedgerFilterOptions,
	setLedgerPage,
	setLedgerSearch,
	setSearchOptions,
	showRecordInTable,
	viewLedgerRecord,
} from "@/store/ledger/ledgerSlice";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* openLedgerWorker(action: PayloadAction<File>) {
	const file = action.payload;
	let opened: Database | null = null;

	try {
		const token: number = beginLedgerOpen();
		const bytes: Uint8Array = yield call(readFileBytes, file);
		const database: Database = yield call(openLedgerDatabase, bytes, token);
		opened = database;
		setLedgerDatabase(database);

		const tables: LedgerTable[] = yield call(readSchema, database);
		yield put(openLedgerSuccess({ fileName: file.name, tables }));
		yield put(loadLedgerRows());
	} catch (error) {
		// The user replaced or removed the ledger mid-import, so there is nothing
		// to report and nothing of theirs to tear down.
		if (error instanceof LedgerImportSuperseded) {
			return;
		}
		// Only what this run installed: a file that fails to open must not take
		// the ledger already loaded with it.
		if (opened) {
			closeLedgerDatabase();
		}
		yield put(
			openLedgerFailure({
				message: getErrorMessage(error),
				cleared: opened !== null,
			}),
		);
	}
}

function* loadLedgerRowsWorker() {
	try {
		const table: string = yield select(selectSelectedLedgerTable);
		if (!table) {
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

		const result: QueryResult = trimmed
			? yield call(searchTable, database, table, trimmed, window)
			: yield call(readTablePage, database, table, window);
		// Filters must reach the count, or the page numbers describe the whole table.
		const total: number = trimmed
			? yield call(countSearchMatches, database, table, trimmed, {
					filters,
					search,
				})
			: yield call(countRows, database, table, { filters, search });

		yield put(loadLedgerRowsSuccess({ result, total }));

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
	} catch (error) {
		yield put(loadLedgerRowsFailure(getErrorMessage(error)));
	}
}

function* exploreLedgerWorker() {
	try {
		const exploreNeedle: string = yield select(selectExploreQuery);
		const trimmed = exploreNeedle.trim();
		if (!trimmed) {
			return;
		}

		const search: SearchOptions = yield select(selectSearchOptions);
		yield put(exploreLedger());
		const matches: LedgerSearchMatch[] = yield call(
			searchLedger,
			getLedgerDatabase(),
			trimmed,
			{ limit: EXPLORE_PREVIEW_LIMIT, search },
		);
		yield put(exploreLedgerSuccess(matches));
	} catch (error) {
		yield put(exploreLedgerFailure(getErrorMessage(error)));
	}
}

function* runLedgerQueryWorker() {
	try {
		const sql: string = yield select(selectLedgerSql);
		if (!sql.trim()) {
			return;
		}

		const result: QueryResult = yield call(
			runReadQuery,
			getLedgerDatabase(),
			sql,
		);
		yield put(runLedgerQuerySuccess(result));

		const tables: LedgerTable[] = yield select(selectLedgerTables);
		const recordTable = matchSingleRecordTable(result, tables);
		if (recordTable) {
			const [record] = toRecords(result);
			if (record) {
				yield put(openLedgerDetail({ table: recordTable, record }));
			}
		}
	} catch (error) {
		yield put(runLedgerQueryFailure(getErrorMessage(error)));
	}
}

function* resolveChainWorker() {
	try {
		const detail: LedgerDetail | null = yield select(selectLedgerDetail);
		if (!detail) {
			return;
		}

		const tables: LedgerTable[] = yield select(selectLedgerTables);
		const chain: LedgerChain = yield call(
			resolveChain,
			getLedgerDatabase(),
			tables,
			detail.table,
			detail.record,
		);
		yield put(resolveChainSuccess(chain));
	} catch (error) {
		yield put(resolveChainFailure(getErrorMessage(error)));
	}
}

function* showRecordInTableWorker(
	action: PayloadAction<{ table: string; record: LedgerRecord }>,
) {
	try {
		const { table, record } = action.payload;
		const page: number = yield call(
			rowPageIndex,
			getLedgerDatabase(),
			table,
			record,
			LEDGER_PAGE_SIZE,
		);
		// setLedgerPage also triggers the row load, so this is the only dispatch.
		yield put(setLedgerPage(page));
	} catch (error) {
		yield put(loadLedgerRowsFailure(getErrorMessage(error)));
	}
}

function* viewLedgerRecordWorker(
	action: PayloadAction<{ table: string; column: string; value: string }>,
) {
	try {
		const { table, column, value } = action.payload;
		const found: QueryResult = yield call(
			findRows,
			getLedgerDatabase(),
			table,
			column,
			value,
			{ limit: 1 },
		);
		const [record] = toRecords(found);
		if (!record) {
			yield put(resolveChainFailure(`No ${table} record found for ${value}`));
			return;
		}
		yield put(pushLedgerDetail({ table, record }));
	} catch (error) {
		yield put(resolveChainFailure(getErrorMessage(error)));
	}
}

function closeLedgerWorker() {
	closeLedgerDatabase();
}

export function* ledgerSaga() {
	yield takeLatest(openLedger.type, openLedgerWorker);
	yield takeLatest(closeLedger.type, closeLedgerWorker);
	yield takeLatest(selectLedgerTable.type, loadLedgerRowsWorker);
	yield takeLatest(loadLedgerRows.type, loadLedgerRowsWorker);
	yield takeLatest(setLedgerPage.type, loadLedgerRowsWorker);
	yield takeLatest(setLedgerFilter.type, loadLedgerRowsWorker);
	// Both searches re-run: the one off screen would otherwise still show results
	// for the previous matching mode when the user switches back to it.
	yield takeLatest(setSearchOptions.type, loadLedgerRowsWorker);
	yield takeLatest(setSearchOptions.type, exploreLedgerWorker);
	yield takeLatest(openTableWithSearch.type, loadLedgerRowsWorker);
	yield takeLatest(showRecordInTable.type, showRecordInTableWorker);
	yield takeLatest(viewLedgerRecord.type, viewLedgerRecordWorker);
	yield debounce(200, setLedgerSearch.type, loadLedgerRowsWorker);
	yield debounce(250, setExploreQuery.type, exploreLedgerWorker);
	yield takeLatest(runLedgerQuery.type, runLedgerQueryWorker);
	yield takeLatest(
		[openLedgerDetail.type, pushLedgerDetail.type, popLedgerDetail.type],
		resolveChainWorker,
	);
}
