import { call, delay, put, select, takeLatest } from "redux-saga/effects";
import { composeDependencies as composeDependenciesRequest } from "@/api/s2dm";
import {
	clearComposeMessage,
	composeDependencies,
	composeDependenciesFailure,
	composeDependenciesSuccess,
	selectAutoPrefix,
	selectPreserveQueryType,
} from "@/store/deps/compose/composeSlice";
import { getErrorMessage } from "@/utils/getErrorMessage";

const COMPOSE_MESSAGE_DISMISS_MS = 4000;

function* composeDependenciesWorker() {
	try {
		const autoPrefix: boolean = yield select(selectAutoPrefix);
		const preserveQueryType: boolean = yield select(selectPreserveQueryType);
		const composedSchema: string = yield call(
			composeDependenciesRequest,
			autoPrefix,
			preserveQueryType,
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
