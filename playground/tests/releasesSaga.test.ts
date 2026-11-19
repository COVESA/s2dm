import { configureStore, type Middleware } from "@reduxjs/toolkit";
import createSagaMiddleware from "redux-saga";
import { afterEach, describe, expect, it, vi } from "vitest";
import type {
	LoadReleaseResponse,
	ReleasePage,
	ReleaseSummary,
} from "@/api/types";
import { releasesSaga } from "@/store/releases/releasesSaga";
import releasesReducer, {
	cancelReleasePageLoad,
	fetchReleasePage,
	fetchReleasePageSuccess,
	openRelease,
	openReleaseFailure,
} from "@/store/releases/releasesSlice";
import uiReducer, { setWorkspace } from "@/store/ui/uiSlice";
import { getLoadedReleaseId } from "@/types/release";
import { getErrorMessage } from "@/utils/getErrorMessage";

const fakeReleases = vi.hoisted(() => {
	type HeldRequest = {
		answer: (reply: unknown) => void;
		fail: (error: Error) => void;
	};
	const pageRequests: HeldRequest[] = [];
	const loadRequests: HeldRequest[] = [];

	/**
	 * Stands in for one API request. It holds the request until the test
	 * answers or fails it.
	 *
	 * @param requests The list that keeps the held requests of one API call.
	 * @returns The reply, which settles only when the test settles it.
	 */
	function holdRequest(requests: HeldRequest[]): Promise<unknown> {
		return new Promise((answer, fail) => {
			requests.push({ answer, fail });
		});
	}

	return {
		pageRequests,
		loadRequests,
		listReleases: () => holdRequest(pageRequests),
		loadRelease: () => holdRequest(loadRequests),
	};
});

vi.mock("@/api/s2dm", async (importOriginal) => {
	const originalModule = await importOriginal<typeof import("@/api/s2dm")>();
	return {
		...originalModule,
		listReleases: fakeReleases.listReleases,
		loadRelease: fakeReleases.loadRelease,
	};
});

const FIRST_REPOSITORY = "https://github.com/owner/first";
const SECOND_REPOSITORY = "https://github.com/owner/second";

const RELEASE_PAGE: ReleasePage = {
	releases: [],
	page: 1,
	has_next: false,
	has_previous: false,
	last_page: 1,
};

const RELEASE: ReleaseSummary = {
	tag: "v1.0.0",
	name: null,
	published_at: null,
	prerelease: false,
	candidate_assets: [{ name: "schema.graphql", size: 1 }],
};

const LOAD_RESPONSE: LoadReleaseResponse = {
	schema_content: "type Query { ping: String }\n",
	schema_id: "release-schema-id",
	metadata: {
		name: "Vehicle",
		id: "vehicle",
		version: "v1.0.0",
		preferred_prefix: null,
	},
};

function startReleasesSaga() {
	const dispatched: unknown[] = [];
	const recordAction: Middleware = () => (next) => (action) => {
		dispatched.push(action);
		return next(action);
	};
	const sagaMiddleware = createSagaMiddleware();
	const store = configureStore({
		reducer: { releases: releasesReducer, ui: uiReducer },
		middleware: (getDefaultMiddleware) =>
			getDefaultMiddleware().concat(recordAction, sagaMiddleware),
	});
	sagaMiddleware.run(releasesSaga);
	return { store, dispatched };
}

type ReleasesStore = ReturnType<typeof startReleasesSaga>["store"];

/** Lets the saga handle the requests that the test settled. */
async function waitForSaga() {
	await new Promise((resolve) => {
		setTimeout(resolve, 0);
	});
}

/**
 * Loads the first release page of a repository and answers it.
 *
 * @param store The store that runs the releases saga.
 * @param repository The repository URL to load.
 */
async function loadRepository(store: ReleasesStore, repository: string) {
	const fetchAction = fetchReleasePage({ repository, page: 1 });
	store.dispatch(fetchAction);
	const pageRequest = fakeReleases.pageRequests.at(-1);
	pageRequest?.answer(RELEASE_PAGE);
	await waitForSaga();
}

afterEach(() => {
	fakeReleases.pageRequests.length = 0;
	fakeReleases.loadRequests.length = 0;
});

describe("releasesSaga", () => {
	it("drops a release page load that the user cancelled", async () => {
		const { store, dispatched } = startReleasesSaga();
		const fetchAction = fetchReleasePage({
			repository: FIRST_REPOSITORY,
			page: 1,
		});
		const cancelAction = cancelReleasePageLoad();

		store.dispatch(fetchAction);
		store.dispatch(cancelAction);
		const [pageRequest] = fakeReleases.pageRequests;
		pageRequest.answer(RELEASE_PAGE);
		await waitForSaga();

		const successActions = dispatched.filter(fetchReleasePageSuccess.match);
		const releasesState = store.getState().releases;
		expect(successActions).toEqual([]);
		expect(releasesState.page).toBeNull();
		expect(releasesState.isLoadingPage).toBe(false);
	});

	it("keeps the shown repository when a load of another repository is cancelled", async () => {
		const { store } = startReleasesSaga();
		await loadRepository(store, FIRST_REPOSITORY);
		const fetchAction = fetchReleasePage({
			repository: SECOND_REPOSITORY,
			page: 1,
		});
		const cancelAction = cancelReleasePageLoad();

		store.dispatch(fetchAction);
		store.dispatch(cancelAction);
		await waitForSaga();

		const releasesState = store.getState().releases;
		expect(releasesState.repository).toBe(FIRST_REPOSITORY);
		expect(releasesState.page).toEqual(RELEASE_PAGE);
	});

	it("clears the open error of the previous repository when another repository loads", async () => {
		const { store } = startReleasesSaga();
		await loadRepository(store, FIRST_REPOSITORY);
		const openFailureAction = openReleaseFailure("Release load failed");
		store.dispatch(openFailureAction);

		await loadRepository(store, SECOND_REPOSITORY);

		const releasesState = store.getState().releases;
		expect(releasesState.repository).toBe(SECOND_REPOSITORY);
		expect(releasesState.openError).toBeNull();
	});

	it("shows the requested repository with its error when its first load fails", async () => {
		const { store } = startReleasesSaga();
		const fetchAction = fetchReleasePage({
			repository: FIRST_REPOSITORY,
			page: 1,
		});
		const requestError = new Error("Repository not found");
		const expectedPageError = getErrorMessage(requestError);

		store.dispatch(fetchAction);
		const [pageRequest] = fakeReleases.pageRequests;
		pageRequest.fail(requestError);
		await waitForSaga();

		const releasesState = store.getState().releases;
		expect(releasesState.repository).toBe(FIRST_REPOSITORY);
		expect(releasesState.page).toBeNull();
		expect(releasesState.pageError).toBe(expectedPageError);
	});

	it("explores a release whose load ends in the Releases workspace", async () => {
		const { store } = startReleasesSaga();
		const workspaceAction = setWorkspace("releases");
		store.dispatch(workspaceAction);
		await loadRepository(store, FIRST_REPOSITORY);
		const openAction = openRelease({
			release: RELEASE,
			artifact: "schema.graphql",
		});
		const loadedReleaseId = getLoadedReleaseId(FIRST_REPOSITORY, RELEASE.tag);

		store.dispatch(openAction);
		const [loadRequest] = fakeReleases.loadRequests;
		loadRequest.answer(LOAD_RESPONSE);
		await waitForSaga();

		const releasesState = store.getState().releases;
		expect(releasesState.openedRelease?.id).toBe(loadedReleaseId);
	});

	it("stores a release without exploring it when its load ends in another workspace", async () => {
		const { store } = startReleasesSaga();
		const releasesWorkspaceAction = setWorkspace("releases");
		store.dispatch(releasesWorkspaceAction);
		await loadRepository(store, FIRST_REPOSITORY);
		const openAction = openRelease({
			release: RELEASE,
			artifact: "schema.graphql",
		});
		const ledgerWorkspaceAction = setWorkspace("ledger");
		const loadedReleaseId = getLoadedReleaseId(FIRST_REPOSITORY, RELEASE.tag);

		store.dispatch(openAction);
		store.dispatch(ledgerWorkspaceAction);
		const [loadRequest] = fakeReleases.loadRequests;
		loadRequest.answer(LOAD_RESPONSE);
		await waitForSaga();

		const releasesState = store.getState().releases;
		const storedReleaseIds = releasesState.loadedReleases.map(
			(loadedRelease) => loadedRelease.id,
		);
		expect(storedReleaseIds).toEqual([loadedReleaseId]);
		expect(releasesState.openedRelease).toBeNull();
		expect(releasesState.openingTag).toBeNull();
	});
});
