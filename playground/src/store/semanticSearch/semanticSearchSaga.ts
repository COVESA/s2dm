import type { PayloadAction } from "@reduxjs/toolkit";
import {
	call,
	debounce,
	put,
	race,
	select,
	take,
	takeLatest,
} from "redux-saga/effects";
import { buildEmbeddings, searchEmbeddings } from "@/api/s2dm";
import { composedSchemaInputs } from "@/api/schemaInputs";
import type { EmbeddingsSearchHit } from "@/api/types";
import {
	type OriginalSchemaPayload,
	setOriginalSchema,
} from "@/store/schema/schemaSlice";
import {
	clearSemanticSearch,
	prepareEmbeddingsFailure,
	prepareEmbeddingsStarted,
	prepareEmbeddingsSuccess,
	resetEmbeddings,
	runSemanticSearch,
	runSemanticSearchFailure,
	runSemanticSearchSuccess,
	SEMANTIC_SEARCH_LIMIT,
	selectEmbeddingsId,
	selectSemanticQuery,
	semanticQueryChanged,
} from "@/store/semanticSearch/semanticSearchSlice";
import { getErrorMessage } from "@/utils/getErrorMessage";

const SEMANTIC_SEARCH_DEBOUNCE_MS = 600;

function* prepareEmbeddingsWorker(
	action: PayloadAction<OriginalSchemaPayload>,
) {
	const { schema: composedSchema, reference } = action.payload;
	if (!composedSchema.trim()) {
		yield put(resetEmbeddings());
		return;
	}

	yield put(prepareEmbeddingsStarted());
	try {
		const schemas = composedSchemaInputs(composedSchema, reference);
		const embeddingsId: string = yield call(buildEmbeddings, schemas);
		yield put(prepareEmbeddingsSuccess(embeddingsId));
		const query: string = yield select(selectSemanticQuery);
		yield put(runSemanticSearch(query));
	} catch (error) {
		yield put(prepareEmbeddingsFailure(getErrorMessage(error)));
	}
}

function* semanticQueryChangedWorker(action: PayloadAction<string>) {
	yield put(runSemanticSearch(action.payload));
}

function* runSemanticSearchWorker(action: PayloadAction<string>) {
	const query = action.payload.trim();
	if (!query) {
		yield put(clearSemanticSearch());
		return;
	}

	const embeddingsId: string | null = yield select(selectEmbeddingsId);
	if (!embeddingsId) {
		yield put(runSemanticSearchFailure("Semantic search is not ready yet."));
		return;
	}

	try {
		const searchRequest = call(
			searchEmbeddings,
			embeddingsId,
			query,
			SEMANTIC_SEARCH_LIMIT,
		);
		const schemaChange = take(setOriginalSchema.type);
		const { hits }: { hits?: EmbeddingsSearchHit[] } = yield race({
			hits: searchRequest,
			schemaChanged: schemaChange,
		});
		// A new schema makes the results stale.
		if (!hits) {
			return;
		}
		const elementIds = hits.map((hit) => hit.id);
		yield put(runSemanticSearchSuccess(elementIds));
	} catch (error) {
		yield put(runSemanticSearchFailure(getErrorMessage(error)));
	}
}

export function* semanticSearchSaga() {
	yield takeLatest(setOriginalSchema.type, prepareEmbeddingsWorker);
	yield debounce(
		SEMANTIC_SEARCH_DEBOUNCE_MS,
		semanticQueryChanged.type,
		semanticQueryChangedWorker,
	);
	yield takeLatest(runSemanticSearch.type, runSemanticSearchWorker);
}
