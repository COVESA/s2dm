import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "@/store/types";

export type EmbeddingsStatus = "idle" | "preparing" | "ready" | "failed";

export interface SemanticSearchState {
	embeddingsId: string | null;
	embeddingsStatus: EmbeddingsStatus;
	embeddingsError: string | null;
	/** The query typed in semantic mode; searched again once new embeddings are ready. */
	query: string;
	/** Ids of the elements matching the last search; `null` when no search is shown. */
	matchedElementIds: string[] | null;
	searchError: string | null;
}

const initialState: SemanticSearchState = {
	embeddingsId: null,
	embeddingsStatus: "idle",
	embeddingsError: null,
	query: "",
	matchedElementIds: null,
	searchError: null,
};

const semanticSearchSlice = createSlice({
	name: "semanticSearch",
	initialState,
	reducers: {
		prepareEmbeddingsStarted: (state) => ({
			...initialState,
			query: state.query,
			embeddingsStatus: "preparing" as const,
		}),
		prepareEmbeddingsSuccess: (state, action: PayloadAction<string>) => {
			state.embeddingsId = action.payload;
			state.embeddingsStatus = "ready";
		},
		prepareEmbeddingsFailure: (state, action: PayloadAction<string>) => {
			state.embeddingsStatus = "failed";
			state.embeddingsError = action.payload;
		},
		resetEmbeddings: (state) => ({ ...initialState, query: state.query }),
		/** The query text changed; the saga searches once typing pauses. */
		semanticQueryChanged: (state, action: PayloadAction<string>) => {
			state.query = action.payload;
		},
		runSemanticSearch: (state, _action: PayloadAction<string>) => {
			state.searchError = null;
		},
		runSemanticSearchSuccess: (state, action: PayloadAction<string[]>) => {
			state.matchedElementIds = action.payload;
		},
		runSemanticSearchFailure: (state, action: PayloadAction<string>) => {
			state.matchedElementIds = null;
			state.searchError = action.payload;
		},
		clearSemanticSearch: (state) => {
			state.query = "";
			state.matchedElementIds = null;
			state.searchError = null;
		},
	},
});

export const {
	prepareEmbeddingsStarted,
	prepareEmbeddingsSuccess,
	prepareEmbeddingsFailure,
	resetEmbeddings,
	semanticQueryChanged,
	runSemanticSearch,
	runSemanticSearchSuccess,
	runSemanticSearchFailure,
	clearSemanticSearch,
} = semanticSearchSlice.actions;

export const selectEmbeddingsId = (state: RootState) =>
	state.semanticSearch.embeddingsId;
export const selectEmbeddingsStatus = (state: RootState) =>
	state.semanticSearch.embeddingsStatus;
export const selectEmbeddingsError = (state: RootState) =>
	state.semanticSearch.embeddingsError;
export const selectSemanticQuery = (state: RootState) =>
	state.semanticSearch.query;
export const selectMatchedElementIds = (state: RootState) =>
	state.semanticSearch.matchedElementIds;
export const selectSemanticSearchError = (state: RootState) =>
	state.semanticSearch.searchError;

export default semanticSearchSlice.reducer;
