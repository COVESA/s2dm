import { all } from "redux-saga/effects";
import { ledgerDetailSaga } from "@/store/ledger/ledgerDetailSaga";
import { ledgerExploreSaga } from "@/store/ledger/ledgerExploreSaga";
import { ledgerFileSaga } from "@/store/ledger/ledgerFileSaga";
import { ledgerQuerySaga } from "@/store/ledger/ledgerQuerySaga";
import { ledgerTableSaga } from "@/store/ledger/ledgerTableSaga";

export function* ledgerSaga() {
	yield all([
		ledgerFileSaga(),
		ledgerTableSaga(),
		ledgerExploreSaga(),
		ledgerQuerySaga(),
		ledgerDetailSaga(),
	]);
}
