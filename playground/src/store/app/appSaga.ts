import { closeInsightDetail } from "@insights-ui/state/insightDetailSlice";
import { closeLedgerDetail } from "@ledger-ui/state/ledgerSlice";
import type { PayloadAction } from "@reduxjs/toolkit";
import { put, takeLatest } from "redux-saga/effects";
import { appStartup, resetApp } from "@/store/app/appSlice";
import {
	computeCapabilities,
	fetchCapabilities,
} from "@/store/capabilities/capabilitiesSlice";
import { clearExportResult } from "@/store/export/exportSlice";
import { resetSchema, setSourceFiles } from "@/store/schema/schemaSlice";
import {
	setAppliedSelectionQuery,
	setSelectionQuery,
} from "@/store/selection/selectionSlice";
import { setExploreTab, setWorkspace } from "@/store/ui/uiSlice";
import { clearValidationErrors } from "@/store/validation/validationSlice";
import type { ImportedFile } from "@/types/importedFile";

function* handleAppStartup() {
	yield put(fetchCapabilities());
}

function* handleResetApp() {
	yield put(resetSchema());
	yield put(setSelectionQuery(""));
	yield put(setAppliedSelectionQuery(""));
	yield put(clearValidationErrors());
	yield put(clearExportResult());
	yield put(computeCapabilities());
}

// Which detail panes exist is the store's business, not a tab handler's. The two
// rules differ: leaving a workspace abandons both stacks, changing explore tab
// only the insights one.
function* handleWorkspaceChanged() {
	yield put(closeInsightDetail());
	yield put(closeLedgerDetail());
}

function* handleExploreTabChanged() {
	yield put(closeInsightDetail());
}

function* handleSourceFilesChanged(action: PayloadAction<ImportedFile[]>) {
	if (action.payload.length > 0) {
		return;
	}

	yield put(resetApp());
}

export function* appSaga() {
	yield takeLatest(appStartup.type, handleAppStartup);
	yield takeLatest(resetApp.type, handleResetApp);
	yield takeLatest(setSourceFiles.type, handleSourceFilesChanged);
	yield takeLatest(setWorkspace.type, handleWorkspaceChanged);
	yield takeLatest(setExploreTab.type, handleExploreTabChanged);
}
