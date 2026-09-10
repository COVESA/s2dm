import { ledgerDetailSaga } from "@ledger-ui/state/ledgerDetailSaga";
import { ledgerExploreSaga } from "@ledger-ui/state/ledgerExploreSaga";
import { ledgerFileSaga } from "@ledger-ui/state/ledgerFileSaga";
import { ledgerQuerySaga } from "@ledger-ui/state/ledgerQuerySaga";
import { ledgerTableSaga } from "@ledger-ui/state/ledgerTableSaga";
import { all } from "redux-saga/effects";

export function* ledgerSaga() {
	yield all([
		ledgerFileSaga(),
		ledgerTableSaga(),
		ledgerExploreSaga(),
		ledgerQuerySaga(),
		ledgerDetailSaga(),
	]);
}
