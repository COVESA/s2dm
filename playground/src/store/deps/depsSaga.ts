import type { PayloadAction } from "@reduxjs/toolkit";
import { call, put, select, takeLatest } from "redux-saga/effects";
import {
	getDependenciesConfig,
	getDependenciesStatus,
	saveDependenciesConfig as saveDependenciesConfigRequest,
} from "@/api/s2dm";
import type {
	DependenciesStatusResponse,
	GetDependenciesConfigResponse,
	SaveDependenciesConfigRequest,
} from "@/api/types";
import { selectExploringDependencyId } from "@/store/deps/dependencyExploration/dependencyExplorationSlice";
import {
	parseDependencyConfig,
	serializeDependencyDraft,
} from "@/store/deps/depsMappers";
import {
	fetchDependenciesConfig,
	fetchDependenciesConfigFailure,
	fetchDependenciesConfigSuccess,
	fetchDependenciesStatus,
	fetchDependenciesStatusFailure,
	fetchDependenciesStatusSuccess,
	importDependenciesConfig,
	importDependenciesConfigFailure,
	importDependenciesConfigSuccess,
	saveDependenciesConfig,
	saveDependenciesConfigFailure,
	saveDependenciesConfigSuccess,
	selectDependencyDrafts,
} from "@/store/deps/depsSlice";
import type { RootState } from "@/store/types";
import type { DependencyDraft } from "@/types/dependency";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* fetchDependenciesStatusWorker() {
	try {
		const response: DependenciesStatusResponse = yield call(
			getDependenciesStatus,
		);
		yield put(fetchDependenciesStatusSuccess(response.status));
	} catch (error) {
		yield put(fetchDependenciesStatusFailure(getErrorMessage(error)));
	}
}

function* fetchDependenciesConfigWorker() {
	try {
		const config: GetDependenciesConfigResponse = yield call(
			getDependenciesConfig,
		);
		// Path-typed selections are not supported in the playground UI.
		const incoming = config.dependencies
			.filter(
				(dependency) =>
					!dependency.selection || dependency.selection.type === "content",
			)
			.map(parseDependencyConfig);

		const exploringId: string | null = yield select(
			selectExploringDependencyId,
		);
		const localDrafts: DependencyDraft[] = yield select(selectDependencyDrafts);

		let localExplored: DependencyDraft | undefined;
		if (exploringId) {
			localExplored = localDrafts.find((draft) => draft.id === exploringId);
		}

		let merged = incoming;
		if (localExplored) {
			merged = incoming.map((draft) => {
				if (draft.id !== exploringId) {
					return draft;
				}
				return {
					...draft,
					selectionType: localExplored.selectionType,
					selectionContent: localExplored.selectionContent,
				};
			});
		}

		yield put(fetchDependenciesConfigSuccess(merged));
	} catch (error) {
		yield put(fetchDependenciesConfigFailure(getErrorMessage(error)));
	}
}

function* saveDependenciesConfigWorker() {
	try {
		const dependencies: ReturnType<typeof selectDependencyDrafts> =
			yield select((state: RootState) => selectDependencyDrafts(state));
		const config: SaveDependenciesConfigRequest = {
			dependencies: dependencies.map(serializeDependencyDraft),
		};

		yield call(saveDependenciesConfigRequest, config);
		yield put(saveDependenciesConfigSuccess());
		yield put(fetchDependenciesStatus());
	} catch (error) {
		yield put(saveDependenciesConfigFailure(getErrorMessage(error)));
	}
}

function* importDependenciesConfigWorker(
	action: PayloadAction<SaveDependenciesConfigRequest>,
) {
	try {
		yield call(saveDependenciesConfigRequest, action.payload);
		yield put(importDependenciesConfigSuccess());
		yield put(fetchDependenciesConfig());
		yield put(fetchDependenciesStatus());
	} catch (error) {
		yield put(importDependenciesConfigFailure(getErrorMessage(error)));
	}
}

export function* depsSaga() {
	yield takeLatest(fetchDependenciesStatus.type, fetchDependenciesStatusWorker);
	yield takeLatest(fetchDependenciesConfig.type, fetchDependenciesConfigWorker);
	yield takeLatest(
		importDependenciesConfig.type,
		importDependenciesConfigWorker,
	);
	yield takeLatest(saveDependenciesConfig.type, saveDependenciesConfigWorker);
}
