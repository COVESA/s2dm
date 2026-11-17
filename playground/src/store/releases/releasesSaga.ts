import type { PayloadAction } from "@reduxjs/toolkit";
import { call, put, race, select, take, takeLatest } from "redux-saga/effects";
import { listReleases, loadRelease, ReleaseArtifactError } from "@/api/s2dm";
import type {
	LoadReleaseResponse,
	ReleasePage,
	ReleaseSummary,
} from "@/api/types";
import {
	cancelReleasePageLoad,
	dismissArchiveChoices,
	exploreRelease,
	type FetchReleasePagePayload,
	fetchReleasePage,
	fetchReleasePageFailure,
	fetchReleasePageSuccess,
	type OpenReleasePayload,
	openRelease,
	openReleaseFailure,
	openReleaseSuccess,
	type ReleasesState,
	selectReleases,
	showArchiveChoices,
} from "@/store/releases/releasesSlice";
import { selectWorkspace, type Workspace } from "@/store/ui/uiSlice";
import { getLoadedReleaseId, type LoadedRelease } from "@/types/release";
import { getErrorMessage } from "@/utils/getErrorMessage";
import {
	listFallbackArchives,
	planReleaseExploration,
} from "@/utils/releaseAssets";

function* fetchReleasePageWorker(
	action: PayloadAction<FetchReleasePagePayload>,
) {
	const repository = action.payload.repository;
	try {
		const pageRequest = call(listReleases, repository, action.payload.page);
		const pageCancel = take(cancelReleasePageLoad.type);
		const result: { page?: ReleasePage; cancel?: unknown } = yield race({
			page: pageRequest,
			cancel: pageCancel,
		});
		if (result.page === undefined) {
			return;
		}
		const successAction = fetchReleasePageSuccess({
			repository,
			page: result.page,
		});
		yield put(successAction);
	} catch (error) {
		const message = getErrorMessage(error);
		const failureAction = fetchReleasePageFailure({ repository, message });
		yield put(failureAction);
	}
}

function* exploreReleaseWorker(action: PayloadAction<ReleaseSummary>) {
	const release = action.payload;
	const releases: ReleasesState = yield select(selectReleases);
	const loadedReleaseId = getLoadedReleaseId(releases.repository, release.tag);
	const storedRelease = releases.loadedReleases.find(
		(loadedRelease) => loadedRelease.id === loadedReleaseId,
	);
	const step = planReleaseExploration(storedRelease, release.candidate_assets);

	if (step.kind === "explore") {
		const successAction = openReleaseSuccess({
			release: step.release,
			shouldExplore: true,
		});
		yield put(successAction);
		return;
	}

	if (step.kind === "open") {
		const openAction = openRelease({ release, artifact: step.artifact });
		yield put(openAction);
		return;
	}

	const choicesAction = showArchiveChoices(step.archives);
	yield put(choicesAction);
}

/**
 * Loads one release asset and stores the loaded release. It sets the opened
 * release only when the selected workspace is `releases` at the end of the
 * load. A first load that fails with an artifact error stores the other
 * archives as archive choices, when there are any. Any other failure stores the
 * open error. A `dismissArchiveChoices` action cancels the running load.
 *
 * @param action The release and the asset to load.
 */
function* openReleaseWorker(action: PayloadAction<OpenReleasePayload>) {
	const { release, artifact } = action.payload;
	const releases: ReleasesState = yield select(selectReleases);
	const repository = releases.repository;

	try {
		const loadRequest = call(loadRelease, {
			repository,
			tag: release.tag,
			artifact,
		});
		const archiveCancel = take(dismissArchiveChoices.type);
		const result: { response?: LoadReleaseResponse; cancel?: unknown } =
			yield race({ response: loadRequest, cancel: archiveCancel });
		const response = result.response;
		if (response === undefined) {
			return;
		}
		const loadedReleaseId = getLoadedReleaseId(repository, release.tag);
		const loadedRelease: LoadedRelease = {
			id: loadedReleaseId,
			repository,
			tag: release.tag,
			artifact,
			name: response.metadata.name,
			version: response.metadata.version,
			schemaContent: response.schema_content,
			schemaId: response.schema_id,
			selectionContent: "",
		};
		const workspace: Workspace = yield select(selectWorkspace);
		const successAction = openReleaseSuccess({
			release: loadedRelease,
			shouldExplore: workspace === "releases",
		});
		yield put(successAction);
	} catch (error) {
		const fallbackArchives = listFallbackArchives(
			release.candidate_assets,
			artifact,
		);
		const isFirstAttempt = releases.archiveChoices === null;
		const canChooseArchive =
			error instanceof ReleaseArtifactError &&
			isFirstAttempt &&
			fallbackArchives.length > 0;
		if (canChooseArchive) {
			const choicesAction = showArchiveChoices(fallbackArchives);
			yield put(choicesAction);
			return;
		}

		const errorMessage = getErrorMessage(error);
		const failureAction = openReleaseFailure(errorMessage);
		yield put(failureAction);
	}
}

export function* releasesSaga() {
	yield takeLatest(fetchReleasePage.type, fetchReleasePageWorker);
	yield takeLatest(exploreRelease.type, exploreReleaseWorker);
	yield takeLatest(openRelease.type, openReleaseWorker);
}
