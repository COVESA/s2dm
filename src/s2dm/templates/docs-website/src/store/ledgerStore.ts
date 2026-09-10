import ledgerDetailReducer from "@ledger-ui/state/ledgerDetailSlice";
import ledgerExploreReducer from "@ledger-ui/state/ledgerExploreSlice";
import ledgerFileReducer from "@ledger-ui/state/ledgerFileSlice";
import ledgerQueryReducer from "@ledger-ui/state/ledgerQuerySlice";
import { ledgerSaga } from "@ledger-ui/state/ledgerSaga";
import ledgerTableReducer from "@ledger-ui/state/ledgerTableSlice";
import { configureStore } from "@reduxjs/toolkit";
import createSagaMiddleware from "redux-saga";

// Separate from the insights store: different route, no shared state, and only
// this one needs saga middleware.
export function createLedgerStore() {
	const sagaMiddleware = createSagaMiddleware();

	const store = configureStore({
		reducer: {
			ledgerFile: ledgerFileReducer,
			ledgerTable: ledgerTableReducer,
			ledgerExplore: ledgerExploreReducer,
			ledgerQuery: ledgerQueryReducer,
			ledgerDetail: ledgerDetailReducer,
		},
		middleware: (getDefaultMiddleware) =>
			// Rows hold Uint8Array blobs, which no serializable check should walk.
			getDefaultMiddleware({
				thunk: false,
				serializableCheck: false,
			}).concat(sagaMiddleware),
	});

	sagaMiddleware.run(ledgerSaga);
	return store;
}

export type LedgerStore = ReturnType<typeof createLedgerStore>;
