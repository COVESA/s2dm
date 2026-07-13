import type { PayloadAction } from "@reduxjs/toolkit";
import { call, put, takeLatest } from "redux-saga/effects";
import { resolveDependencies as resolveDependenciesRequest } from "@/api/s2dm";
import {
	fetchDependenciesConfig,
	fetchDependenciesStatus,
} from "@/store/deps/depsSlice";
import {
	resolveDependencies,
	resolveDependenciesFailure,
	resolveDependenciesSuccess,
} from "@/store/deps/resolve/resolveSlice";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* resolveDependenciesWorker(action: PayloadAction<{ clean: boolean }>) {
	try {
		const warnings: string[] = yield call(
			resolveDependenciesRequest,
			action.payload.clean,
		);
		yield put(resolveDependenciesSuccess(warnings));
		yield put(fetchDependenciesConfig());
		yield put(fetchDependenciesStatus());
	} catch (error) {
		yield put(resolveDependenciesFailure(getErrorMessage(error)));
	}
}

export function* depsResolveSaga() {
	yield takeLatest(resolveDependencies.type, resolveDependenciesWorker);
}
