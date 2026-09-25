import type { PayloadAction } from "@reduxjs/toolkit";
import { call, put, select, takeLatest } from "redux-saga/effects";
import { findOne, resolveChain } from "@/ledger/chainResolve";
import type { LedgerChain } from "@/ledger/chainSpec";

import { LEDGER_PAGE_SIZE, rowPageIndex } from "@/ledger/rows";
import { getLedgerDatabase } from "@/ledger/session";
import type { LedgerRecord, LedgerTable } from "@/ledger/types";
import type { LedgerDetail } from "@/store/ledger/ledgerSlice";
import {
	clearLedgerChain,
	loadLedgerRowsFailure,
	openLedgerDetail,
	popLedgerDetail,
	pushLedgerDetail,
	resolveChainFailure,
	resolveChainSuccess,
	selectLedgerDetail,
	selectLedgerTables,
	setLedgerPage,
	showRecordInTable,
	viewLedgerRecord,
} from "@/store/ledger/ledgerSlice";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* resolveChainWorker() {
	try {
		const detail: LedgerDetail | null = yield select(selectLedgerDetail);
		if (!detail) {
			return;
		}

		if (detail.kind !== "row") {
			yield put(clearLedgerChain());
			return;
		}

		const tables: LedgerTable[] = yield select(selectLedgerTables);
		const database = getLedgerDatabase();
		const chain: LedgerChain = yield call(
			resolveChain,
			database,
			tables,
			detail.table,
			detail.record,
		);
		yield put(resolveChainSuccess(chain));
	} catch (error) {
		const message = getErrorMessage(error);
		yield put(resolveChainFailure(message));
	}
}

function* showRecordInTableWorker(
	action: PayloadAction<{ table: string; record: LedgerRecord }>,
) {
	try {
		const { table, record } = action.payload;
		const database = getLedgerDatabase();
		const page: number = yield call(
			rowPageIndex,
			database,
			table,
			record,
			LEDGER_PAGE_SIZE,
		);
		// setLedgerPage also triggers the row load, so this is the only dispatch.
		yield put(setLedgerPage(page));
	} catch (error) {
		const message = getErrorMessage(error);
		yield put(loadLedgerRowsFailure(message));
	}
}

function* viewLedgerRecordWorker(
	action: PayloadAction<{ table: string; column: string; value: string }>,
) {
	try {
		const { table, column, value } = action.payload;
		const database = getLedgerDatabase();
		const record: LedgerRecord | null = yield call(
			findOne,
			database,
			table,
			column,
			value,
		);
		if (!record) {
			yield put(resolveChainFailure(`No ${table} record found for ${value}`));
			return;
		}
		yield put(pushLedgerDetail({ kind: "row", table, record }));
	} catch (error) {
		const message = getErrorMessage(error);
		yield put(resolveChainFailure(message));
	}
}

export function* ledgerDetailSaga() {
	yield takeLatest(showRecordInTable.type, showRecordInTableWorker);
	yield takeLatest(viewLedgerRecord.type, viewLedgerRecordWorker);
	yield takeLatest(
		[openLedgerDetail.type, pushLedgerDetail.type, popLedgerDetail.type],
		resolveChainWorker,
	);
}
