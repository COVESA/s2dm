import { call, put, select, takeLatest } from "redux-saga/effects";
import { runReadQuery } from "@/ledger/query";
import { tableToAutoOpen } from "@/ledger/resultRecord";
import { toRecords } from "@/ledger/rows";
import { getLedgerDatabase } from "@/ledger/session";
import type { LedgerTable, QueryResult } from "@/ledger/types";
import {
	openLedgerDetail,
	runLedgerQuery,
	runLedgerQueryFailure,
	runLedgerQuerySuccess,
	selectLedgerSql,
	selectLedgerTables,
} from "@/store/ledger/ledgerSlice";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* runLedgerQueryWorker() {
	try {
		const sql: string = yield select(selectLedgerSql);
		if (!sql.trim()) {
			yield put(runLedgerQueryFailure("Enter a query to run."));
			return;
		}

		const database = getLedgerDatabase();
		const result: QueryResult = yield call(runReadQuery, database, sql);
		yield put(runLedgerQuerySuccess(result));

		const tables: LedgerTable[] = yield select(selectLedgerTables);
		const recordTable = tableToAutoOpen(result, tables);
		if (recordTable) {
			const [record] = toRecords(result);
			if (record) {
				yield put(
					openLedgerDetail({ kind: "row", table: recordTable, record }),
				);
			}
		}
	} catch (error) {
		const message = getErrorMessage(error);
		yield put(runLedgerQueryFailure(message));
	}
}

export function* ledgerQuerySaga() {
	yield takeLatest(runLedgerQuery.type, runLedgerQueryWorker);
}
