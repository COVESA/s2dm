import type { PayloadAction } from "@reduxjs/toolkit";
import { put, takeLatest } from "redux-saga/effects";
import { appStartup, resetApp } from "@/store/app/appSlice";
import {
	computeCapabilities,
	fetchCapabilities,
} from "@/store/capabilities/capabilitiesSlice";
import { clearExportResult } from "@/store/export/exportSlice";
import {
	resetSchema,
	setSourceFiles,
} from "@/store/schema/schemaSlice";
import { resetSelectionQuery } from "@/store/selection/selectionSlice";
import { clearValidationErrors } from "@/store/validation/validationSlice";
import type { ImportedFile } from "@/types/importedFile";

function* handleAppStartup() {
	yield put(fetchCapabilities());
}

function* handleResetApp() {
	yield put(resetSchema());
	yield put(resetSelectionQuery());
	yield put(clearValidationErrors());
	yield put(clearExportResult());
	yield put(computeCapabilities());
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
}
