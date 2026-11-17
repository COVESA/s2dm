import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { ReleaseAsset, ReleasePage, ReleaseSummary } from "@/api/types";
import type { RootState } from "@/store/types";
import {
	addLoadedRelease,
	type LoadedRelease,
	setLoadedReleaseSelection,
} from "@/types/release";

export type FetchReleasePagePayload = {
	repository: string;
	page: number;
};

export type ReleasePageResult = {
	repository: string;
	page: ReleasePage;
};

export type ReleasePageError = {
	repository: string;
	message: string;
};

export type OpenReleasePayload = {
	release: ReleaseSummary;
	artifact: string;
};

export type OpenReleaseResult = {
	release: LoadedRelease;
	shouldExplore: boolean;
};

export type SetReleaseSelectionPayload = {
	releaseId: string;
	value: string;
};

export interface ReleasesState {
	loadedReleases: LoadedRelease[];
	repositoryInput: string;
	repository: string;
	page: ReleasePage | null;
	selectedRelease: ReleaseSummary | null;
	isLoadingPage: boolean;
	pageError: string | null;
	openingTag: string | null;
	openError: string | null;
	archiveChoices: ReleaseAsset[] | null;
	openedRelease: LoadedRelease | null;
}

const initialState: ReleasesState = {
	loadedReleases: [],
	repositoryInput: "",
	repository: "",
	page: null,
	selectedRelease: null,
	isLoadingPage: false,
	pageError: null,
	openingTag: null,
	openError: null,
	archiveChoices: null,
	openedRelease: null,
};

/**
 * Makes a repository the current one. Another repository drops the page, the
 * selected release and the open error of the previous one. It changes the
 * given state draft.
 *
 * @param state The releases state draft.
 * @param repository The repository URL of the answered request.
 */
function showRepository(state: ReleasesState, repository: string) {
	if (state.repository === repository) {
		return;
	}
	state.repository = repository;
	state.page = null;
	state.selectedRelease = null;
	state.openError = null;
}

const releasesSlice = createSlice({
	name: "releases",
	initialState,
	reducers: {
		setRepositoryInput: (state, action: PayloadAction<string>) => {
			state.repositoryInput = action.payload;
		},
		fetchReleasePage: (
			state,
			_action: PayloadAction<FetchReleasePagePayload>,
		) => {
			state.isLoadingPage = true;
			state.pageError = null;
		},
		fetchReleasePageSuccess: (
			state,
			action: PayloadAction<ReleasePageResult>,
		) => {
			showRepository(state, action.payload.repository);
			state.page = action.payload.page;
			state.isLoadingPage = false;
		},
		fetchReleasePageFailure: (
			state,
			action: PayloadAction<ReleasePageError>,
		) => {
			showRepository(state, action.payload.repository);
			state.isLoadingPage = false;
			state.pageError = action.payload.message;
		},
		exploreRelease: (state, action: PayloadAction<ReleaseSummary>) => {
			state.selectedRelease = action.payload;
			state.openError = null;
		},
		openRelease: (state, action: PayloadAction<OpenReleasePayload>) => {
			state.openingTag = action.payload.release.tag;
			state.openError = null;
		},
		openReleaseSuccess: (state, action: PayloadAction<OpenReleaseResult>) => {
			const addition = addLoadedRelease(
				state.loadedReleases,
				action.payload.release,
			);
			state.loadedReleases = addition.loadedReleases;
			state.openingTag = null;
			state.archiveChoices = null;
			if (action.payload.shouldExplore) {
				state.openedRelease = addition.openedRelease;
			}
		},
		openReleaseFailure: (state, action: PayloadAction<string>) => {
			state.openingTag = null;
			state.openError = action.payload;
		},
		showArchiveChoices: (state, action: PayloadAction<ReleaseAsset[]>) => {
			state.archiveChoices = action.payload;
			state.openingTag = null;
			state.openError = null;
		},
		dismissArchiveChoices: (state) => {
			state.archiveChoices = null;
			state.openingTag = null;
			state.openError = null;
		},
		clearOpenedRelease: (state) => {
			state.openedRelease = null;
		},
		clearRepository: (state) => {
			state.repository = "";
			state.page = null;
			state.selectedRelease = null;
			state.isLoadingPage = false;
			state.pageError = null;
			state.openingTag = null;
			state.openError = null;
			state.archiveChoices = null;
		},
		cancelReleasePageLoad: (state) => {
			state.isLoadingPage = false;
		},
		setReleaseSelection: (
			state,
			action: PayloadAction<SetReleaseSelectionPayload>,
		) => {
			state.loadedReleases = setLoadedReleaseSelection(
				state.loadedReleases,
				action.payload.releaseId,
				action.payload.value,
			);
		},
	},
});

export const {
	setRepositoryInput,
	fetchReleasePage,
	fetchReleasePageSuccess,
	fetchReleasePageFailure,
	exploreRelease,
	openRelease,
	openReleaseSuccess,
	openReleaseFailure,
	showArchiveChoices,
	dismissArchiveChoices,
	clearOpenedRelease,
	clearRepository,
	cancelReleasePageLoad,
	setReleaseSelection,
} = releasesSlice.actions;

export const selectLoadedReleases = (state: RootState) =>
	state.releases.loadedReleases;
export const selectReleases = (state: RootState) => state.releases;
export const selectOpenedRelease = (state: RootState) =>
	state.releases.openedRelease;

export default releasesSlice.reducer;
