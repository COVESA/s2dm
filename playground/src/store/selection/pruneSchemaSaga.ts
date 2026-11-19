import type { PayloadAction } from "@reduxjs/toolkit";
import { call, put, select, takeLatest } from "redux-saga/effects";
import { ApiValidationError, filterSchema } from "@/api/s2dm";
import { mapImportedFilesToSchemaInputs } from "@/api/schemaInputs";
import type { ExportResponse, QueryInput, SchemaInput } from "@/api/types";
import {
	saveDependenciesConfig,
	updateDependencyField,
} from "@/store/deps/depsSlice";
import {
	selectExploredSchemaContent,
	selectExploringDependencyId,
	selectExploringReleaseId,
} from "@/store/exploration/explorationSlice";
import { setReleaseSelection } from "@/store/releases/releasesSlice";
import { selectComposedSources } from "@/store/schema/composedSources";
import {
	selectOriginalSchema,
	setFilteredSchema,
} from "@/store/schema/schemaSlice";
import {
	clearAppliedSelection,
	pruningFailure,
	pruningStart,
	pruningSuccess,
	resetSelection,
} from "@/store/selection/selectionSlice";
import type { SchemaSource } from "@/types/schemaSource";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* persistExploredSelection(value: string) {
	const exploringReleaseId: string | null = yield select(
		selectExploringReleaseId,
	);
	if (exploringReleaseId) {
		const selectionAction = setReleaseSelection({
			releaseId: exploringReleaseId,
			value,
		});
		yield put(selectionAction);
		return;
	}

	const exploringDependencyId: string | null = yield select(
		selectExploringDependencyId,
	);
	if (!exploringDependencyId) {
		return;
	}
	yield put(
		updateDependencyField({
			dependencyId: exploringDependencyId,
			field: "selectionContent",
			value,
		}),
	);
	yield put(saveDependenciesConfig());
}

function* pruneSchemaWorker(action: PayloadAction<string>) {
	const query = action.payload;
	const originalSchema: string = yield select(selectOriginalSchema);

	if (query.trim() === "") {
		yield put(setFilteredSchema(originalSchema));
		yield put(pruningSuccess(""));
		return;
	}

	const sources: SchemaSource[] = yield select(selectComposedSources);
	const exploredSchemaContent: string | null | undefined = yield select(
		selectExploredSchemaContent,
	);

	try {
		let schemas: SchemaInput[];
		if (exploredSchemaContent?.trim()) {
			schemas = [
				{
					type: "content",
					content: exploredSchemaContent,
				},
			];
		} else {
			schemas = mapImportedFilesToSchemaInputs(sources);
		}

		const selectionQuery: QueryInput = { type: "content", content: query };

		const response: ExportResponse = yield call(
			filterSchema,
			schemas,
			selectionQuery,
		);
		const prunedSchema = response.result[0] || "";

		yield put(setFilteredSchema(prunedSchema));
		yield put(pruningSuccess(query));
	} catch (err) {
		let errorMsg: string;
		if (err instanceof ApiValidationError) {
			errorMsg = err.errors.join("\n");
		} else {
			errorMsg = getErrorMessage(err);
		}
		console.error("Failed to prune schema:", err);
		yield put(setFilteredSchema(originalSchema));
		yield put(pruningFailure(errorMsg));
	}
}

function* pruningSuccessWorker(action: PayloadAction<string>) {
	yield* persistExploredSelection(action.payload);
}

function* clearAppliedSelectionWorker() {
	const originalSchema: string = yield select(selectOriginalSchema);
	yield put(setFilteredSchema(originalSchema));
}

function* resetSelectionWorker() {
	const originalSchema: string = yield select(selectOriginalSchema);
	yield put(setFilteredSchema(originalSchema));
	yield* persistExploredSelection("");
}

export function* pruneSchemaSaga() {
	yield takeLatest(pruningStart.type, pruneSchemaWorker);
	yield takeLatest(pruningSuccess.type, pruningSuccessWorker);
	yield takeLatest(clearAppliedSelection.type, clearAppliedSelectionWorker);
	yield takeLatest(resetSelection.type, resetSelectionWorker);
}
