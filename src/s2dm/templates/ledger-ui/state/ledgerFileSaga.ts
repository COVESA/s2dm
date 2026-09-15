import {
	closeLedgerWorker,
	LedgerWorkCancelled,
	openLedgerInWorker,
} from "@ledger-ui/data/ledgerClient";
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
import { getErrorMessage } from "@/utils/getErrorMessage";

function* openLedgerWorker(
	action: PayloadAction<{ name: string; bytes: Uint8Array }>,
) {
	const { name, bytes } = action.payload;

	try {
		const tables: LedgerTable[] = yield call(openLedgerInWorker, bytes);
		yield put(openLedgerSuccess({ fileName: name, tables }));
		yield put(loadLedgerRows());
	} catch (error) {
		// The reader removed or replaced the ledger mid-import, so there is nothing
		// of theirs to report on.
		if (error instanceof LedgerWorkCancelled) {
			return;
		}
		// Nothing was cleared: the client only adopts a worker once its database
		// is readable, so the ledger already loaded is still the one loaded.
		yield put(
			openLedgerFailure({ message: getErrorMessage(error), cleared: false }),
		);
	}
}

function closeLedgerWork() {
	closeLedgerWorker();
}

export function* ledgerFileSaga() {
	yield takeLatest(openLedger.type, openLedgerWorker);
	yield takeLatest(closeLedger.type, closeLedgerWork);
}
