import { put, takeLatest } from "redux-saga/effects";
import { appStartup, resetApp } from "@/store/app/appSlice";
import {
	computeCapabilities,
	fetchCapabilities,
} from "@/store/capabilities/capabilitiesSlice";
import { clearExportResult } from "@/store/export/exportSlice";
import { resetSchema } from "@/store/schema/schemaSlice";
import { resetSelectionQuery } from "@/store/selection/selectionSlice";

function* handleAppStartup() {
	yield put(fetchCapabilities());
}

function* handleResetApp() {
	yield put(resetSchema());
	yield put(resetSelectionQuery());
	yield put(clearExportResult());
	yield put(computeCapabilities());
}

export function* appSaga() {
	yield takeLatest(appStartup.type, handleAppStartup);
	yield takeLatest(resetApp.type, handleResetApp);
}
