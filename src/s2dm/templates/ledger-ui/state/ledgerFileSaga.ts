import { readSchema } from "@ledger-ui/data/schema";
import {
	beginLedgerOpen,
	closeLedgerDatabase,
	setLedgerDatabase,
} from "@ledger-ui/data/session";
import {
	LedgerImportSuperseded,
	openLedgerDatabase,
} from "@ledger-ui/data/sqlite";
import type { LedgerTable } from "@ledger-ui/data/types";
import {
	closeLedger,
	loadLedgerRows,
	openLedger,
	openLedgerFailure,
	openLedgerSuccess,
} from "@ledger-ui/state/ledgerSlice";
import type { PayloadAction } from "@reduxjs/toolkit";
import { call, put, takeLatest } from "redux-saga/effects";
import type { Database } from "sql.js";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* openLedgerWorker(
	action: PayloadAction<{ name: string; bytes: Uint8Array }>,
) {
	const { name, bytes } = action.payload;
	let opened: Database | null = null;

	try {
		const token: number = beginLedgerOpen();
		const database: Database = yield call(openLedgerDatabase, bytes, token);
		opened = database;
		setLedgerDatabase(database);

		const tables: LedgerTable[] = yield call(readSchema, database);
		yield put(openLedgerSuccess({ fileName: name, tables }));
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

function closeLedgerWorker() {
	closeLedgerDatabase();
}

export function* ledgerFileSaga() {
	yield takeLatest(openLedger.type, openLedgerWorker);
	yield takeLatest(closeLedger.type, closeLedgerWorker);
}
