import {
	closeLedger,
	openLedger,
	openLedgerFailure,
} from "@ledger-ui/state/ledgerActions";
import ledgerDetailReducer from "@ledger-ui/state/ledgerDetailSlice";
import ledgerExploreReducer from "@ledger-ui/state/ledgerExploreSlice";
import ledgerFileReducer from "@ledger-ui/state/ledgerFileSlice";
import ledgerQueryReducer from "@ledger-ui/state/ledgerQuerySlice";
import { ledgerSaga } from "@ledger-ui/state/ledgerSaga";
import ledgerTableReducer from "@ledger-ui/state/ledgerTableSlice";
import { configureStore } from "@reduxjs/toolkit";
import createSagaMiddleware from "redux-saga";
import { getErrorMessage } from "@/utils/getErrorMessage";

// Separate from the insights store: different route, no shared state, and only
// this one needs saga middleware.
function createLedgerStore() {
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

	const task = sagaMiddleware.run(ledgerSaga);
	return { store, stop: () => task.cancel() };
}

export type LedgerSession = ReturnType<typeof createLedgerStore>;

// Held at module scope because each ledger view is its own route: the page
// remounts on every sidebar click, and a session per mount would re-download
// and re-parse the whole ledger each time.
let session: LedgerSession | null = null;
let loading: AbortController | null = null;

/**
 * The session for this reader, opening the ledger the first time it is asked for.
 *
 * The download belongs to the session rather than to whichever view is mounted,
 * so switching view mid-download neither cancels it nor starts a second one, and
 * a failure is dispatched into the store where it outlives the switch.
 */
export function openLedgerOnce(options: {
	url: string;
	name: string;
}): LedgerSession {
	if (session) {
		return session;
	}

	const opened = createLedgerStore();
	session = opened;
	const controller = new AbortController();
	loading = controller;

	fetch(options.url, { signal: controller.signal })
		.then((response) => {
			if (!response.ok) {
				throw new Error(`HTTP ${response.status}`);
			}
			return response.arrayBuffer();
		})
		.then((buffer) => {
			opened.store.dispatch(
				openLedger({ name: options.name, bytes: new Uint8Array(buffer) }),
			);
		})
		.catch((reason: unknown) => {
			if (controller.signal.aborted) {
				return;
			}
			opened.store.dispatch(
				openLedgerFailure({ message: getErrorMessage(reason), cleared: false }),
			);
		});

	return opened;
}

// Called when leaving the ledger, not when moving between its views: the
// database sits decoded in wasm memory until something releases it.
export function releaseLedgerSession(): void {
	loading?.abort();
	loading = null;
	if (!session) {
		return;
	}
	session.store.dispatch(closeLedger());
	session.stop();
	session = null;
}
