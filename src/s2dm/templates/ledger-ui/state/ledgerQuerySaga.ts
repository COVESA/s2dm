import { callLedger, cancelLedgerWork } from "@ledger-ui/data/ledgerClient";
import { toRecord } from "@ledger-ui/data/rows";
import type { LedgerRecord, QueryResult } from "@ledger-ui/data/types";
import {
	cancelLedgerQuery,
	openLedgerDetail,
	openLedgerQueryRow,
	runLedgerQuery,
	runLedgerQueryFailure,
	runLedgerQuerySuccess,
	selectLedgerQueryResult,
	selectLedgerSql,
} from "@ledger-ui/state/ledgerSlice";
import {
	call,
	cancelled,
	delay,
	put,
	race,
	select,
	take,
	takeLatest,
} from "redux-saga/effects";
import { getErrorMessage } from "@/utils/getErrorMessage";

// Long enough that an honest scan of a large ledger still finishes.
const QUERY_DEADLINE_MS = 30_000;

function* runLedgerQueryWorker() {
	try {
		const sql: string = yield select(selectLedgerSql);
		if (!sql.trim()) {
			yield put(runLedgerQueryFailure("Enter a query to run."));
			return;
		}

		const outcome: {
			result?: QueryResult;
			stopped?: unknown;
			overran?: true;
		} = yield race({
			result: call(callLedger, "runQuery", { sql }),
			stopped: take(cancelLedgerQuery.type),
			overran: delay(QUERY_DEADLINE_MS),
		});

		const { result } = outcome;
		if (!result) {
			const reason = outcome.stopped
				? "The query was cancelled."
				: `The query was still running after ${QUERY_DEADLINE_MS / 1000} seconds and was stopped.`;
			yield call(cancelLedgerWork, reason);
			yield put(runLedgerQueryFailure(reason));
			return;
		}
		yield put(runLedgerQuerySuccess(result));
		yield* openLoneRecord(result);
	} catch (error) {
		const message = getErrorMessage(error);
		yield put(runLedgerQueryFailure(message));
	} finally {
		// The replaced task's query would otherwise hold the worker against the new.
		const replaced: boolean = yield cancelled();
		if (replaced) {
			yield call(cancelLedgerWork, "The query was replaced by a newer one.");
		}
	}
}

// A projection is not opened: it carries no context, and the reader asked for
// none. Its own try, because the rows are on screen and must stay there.
function* openLoneRecord(result: QueryResult) {
	const [row] = result.rows;
	if (result.rows.length !== 1 || !row) {
		return;
	}
	try {
		const record = toRecord(row, result.columns);
		const table: string | null = yield* findStoredTable(record, result.columns);
		if (table) {
			yield put(openLedgerDetail({ kind: "row", table, record }));
		}
	} catch {
		// Leaves the result listed and nothing selected.
	}
}

// The table that holds this row, or null when no table does.
function* findStoredTable(record: LedgerRecord, columns: string[]) {
	const table: string | null = yield call(callLedger, "storedRecordTable", {
		columns,
		record,
	});
	return table;
}

function* openLedgerQueryRowWorker(
	action: ReturnType<typeof openLedgerQueryRow>,
) {
	const result: QueryResult | null = yield select(selectLedgerQueryResult);
	if (!result) {
		return;
	}
	const { record, cells } = action.payload;
	try {
		const table: string | null = yield* findStoredTable(record, result.columns);
		yield put(
			openLedgerDetail(
				table
					? { kind: "row", table, record }
					: { kind: "projection", record, cells },
			),
		);
	} catch {
		// A row that cannot be verified is a projection, as it is when unmatched.
		yield put(openLedgerDetail({ kind: "projection", record, cells }));
	}
}

export function* ledgerQuerySaga() {
	yield takeLatest(runLedgerQuery.type, runLedgerQueryWorker);
	yield takeLatest(openLedgerQueryRow.type, openLedgerQueryRowWorker);
}
