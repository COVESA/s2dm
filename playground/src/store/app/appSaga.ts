import { closeInsightDetail } from "@insights-ui/state/insightDetailSlice";
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

/**
 * Closes the insights details when the workspace or the explore tab changes.
 * Which detail panes exist is the store's business, not a tab handler's. The
 * ledger details stay open, so returning to the ledger workspace shows the same
 * record selected.
 *
 * @returns An iterator of the saga's effects.
 */
function* handleTabChanged() {
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
	yield takeLatest([setWorkspace.type, setExploreTab.type], handleTabChanged);
}
