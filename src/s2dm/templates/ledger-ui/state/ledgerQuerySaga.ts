import { runReadQuery } from "@ledger-ui/data/query";
import { tableToAutoOpen } from "@ledger-ui/data/resultRecord";
import { toRecords } from "@ledger-ui/data/rows";
import { getLedgerDatabase } from "@ledger-ui/data/session";
import type { LedgerTable, QueryResult } from "@ledger-ui/data/types";
import {
	openLedgerDetail,
	runLedgerQuery,
	runLedgerQueryFailure,
	runLedgerQuerySuccess,
	selectLedgerSql,
	selectLedgerTables,
} from "@ledger-ui/state/ledgerSlice";
import { call, put, select, takeLatest } from "redux-saga/effects";
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
