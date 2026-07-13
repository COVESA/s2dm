import type { PayloadAction } from "@reduxjs/toolkit";
import { call, delay, put, takeLatest } from "redux-saga/effects";
import { composeDependencies as composeDependenciesRequest } from "@/api/s2dm";
import {
	clearComposeMessage,
	composeDependencies,
	composeDependenciesFailure,
	composeDependenciesSuccess,
} from "@/store/deps/compose/composeSlice";
import { getErrorMessage } from "@/utils/getErrorMessage";

const COMPOSE_MESSAGE_DISMISS_MS = 4000;

function* composeDependenciesWorker(
	action: PayloadAction<{ autoPrefix: boolean }>,
) {
	try {
		const composedSchema: string = yield call(
			composeDependenciesRequest,
			action.payload.autoPrefix,
		);
		yield put(composeDependenciesSuccess(composedSchema));
		yield delay(COMPOSE_MESSAGE_DISMISS_MS);
		yield put(clearComposeMessage());
	} catch (error) {
		yield put(composeDependenciesFailure(getErrorMessage(error)));
	}
}

export function* depsComposeSaga() {
	yield takeLatest(composeDependencies.type, composeDependenciesWorker);
}
