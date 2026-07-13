import type { PayloadAction } from "@reduxjs/toolkit";
import { call, put, select, takeLatest } from "redux-saga/effects";
import {
	getDependenciesIdentities,
	saveDependenciesIdentities as saveDependenciesIdentitiesRequest,
} from "@/api/s2dm";
import type { DependenciesIdentities } from "@/api/types";
import {
	parseDependencyIdentity,
	serializeDependencyIdentityDraft,
} from "@/store/deps/identities/identitiesMappers";
import {
	fetchIdentities,
	fetchIdentitiesFailure,
	fetchIdentitiesSuccess,
	importIdentitiesFile,
	importIdentitiesFileFailure,
	importIdentitiesFileSuccess,
	saveIdentities,
	saveIdentitiesFailure,
	saveIdentitiesSuccess,
	selectIdentityDrafts,
} from "@/store/deps/identities/identitiesSlice";
import type { RootState } from "@/store/types";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* fetchIdentitiesWorker() {
	try {
		const identities: DependenciesIdentities = yield call(
			getDependenciesIdentities,
		);
		yield put(
			fetchIdentitiesSuccess(
				identities.identities.map(parseDependencyIdentity),
			),
		);
	} catch (error) {
		yield put(fetchIdentitiesFailure(getErrorMessage(error)));
	}
}

function* saveIdentitiesWorker() {
	try {
		const identities: ReturnType<typeof selectIdentityDrafts> = yield select(
			(state: RootState) => selectIdentityDrafts(state),
		);
		const payload: DependenciesIdentities = {
			identities: identities.map(serializeDependencyIdentityDraft),
		};

		yield call(saveDependenciesIdentitiesRequest, payload);
		yield put(saveIdentitiesSuccess());
	} catch (error) {
		yield put(saveIdentitiesFailure(getErrorMessage(error)));
	}
}

function* importIdentitiesFileWorker(
	action: PayloadAction<DependenciesIdentities>,
) {
	try {
		yield call(saveDependenciesIdentitiesRequest, action.payload);
		yield put(importIdentitiesFileSuccess());
		yield put(fetchIdentities());
	} catch (error) {
		yield put(importIdentitiesFileFailure(getErrorMessage(error)));
	}
}

export function* depsIdentitiesSaga() {
	yield takeLatest(fetchIdentities.type, fetchIdentitiesWorker);
	yield takeLatest(importIdentitiesFile.type, importIdentitiesFileWorker);
	yield takeLatest(saveIdentities.type, saveIdentitiesWorker);
}
