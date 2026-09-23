import type { LedgerChain } from "@ledger-ui/data/chainSpec";
import { callLedger } from "@ledger-ui/data/ledgerClient";
import { LEDGER_PAGE_SIZE } from "@ledger-ui/data/rows";
import type { LedgerRecord } from "@ledger-ui/data/types";
import type { LedgerDetail } from "@ledger-ui/state/ledgerSlice";
import {
	clearLedgerChain,
	loadLedgerRowsFailure,
	openLedgerDetail,
	popLedgerDetail,
	pushLedgerDetail,
	resolveChainFailure,
	resolveChainSuccess,
	selectLedgerDetail,
	setLedgerPage,
	showRecordInTable,
	viewLedgerRecord,
} from "@ledger-ui/state/ledgerSlice";
import type { PayloadAction } from "@reduxjs/toolkit";
import { call, put, select, takeLatest } from "redux-saga/effects";
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

		const chain: LedgerChain = yield call(callLedger, "resolveChain", {
			table: detail.table,
			record: detail.record,
		});
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
		const page: number = yield call(callLedger, "rowPageIndex", {
			table,
			record,
			pageSize: LEDGER_PAGE_SIZE,
		});
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
		const record: LedgerRecord | null = yield call(callLedger, "findOne", {
			table,
			column,
			value,
		});
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
