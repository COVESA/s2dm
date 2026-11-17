import { call, put, select, takeLatest } from "redux-saga/effects";
import { resolveDependencies as resolveDependenciesRequest } from "@/api/s2dm";
import {
	fetchDependenciesConfig,
	fetchDependenciesStatus,
} from "@/store/deps/depsSlice";
import {
	resolveDependencies,
	resolveDependenciesFailure,
	resolveDependenciesSuccess,
	selectCleanBeforeResolve,
} from "@/store/deps/resolve/resolveSlice";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* resolveDependenciesWorker() {
	try {
		const cleanBeforeResolve: boolean = yield select(selectCleanBeforeResolve);
		const warnings: string[] = yield call(
			resolveDependenciesRequest,
			cleanBeforeResolve,
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
