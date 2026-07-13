import type { PayloadAction } from "@reduxjs/toolkit";
import { call, put, select, takeLatest } from "redux-saga/effects";
import { ApiValidationError, filterSchema } from "@/api/s2dm";
import { mapImportedFilesToSchemaInputs } from "@/api/schemaInputs";
import type { ExportResponse, QueryInput, SchemaInput } from "@/api/types";
import { selectExploringDependencyId } from "@/store/deps/dependencyExploration/dependencyExplorationSlice";
import {
	saveDependenciesConfig,
	selectDependencyDrafts,
	updateDependencyField,
} from "@/store/deps/depsSlice";
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
import type { DependencyDraft } from "@/types/dependency";
import type { SchemaSource } from "@/types/schemaSource";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* persistExploringDependencySelection(value: string) {
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
	const dependencies: DependencyDraft[] = yield select(selectDependencyDrafts);
	const exploringDependencyId: string | null = yield select(
		selectExploringDependencyId,
	);
	const exploringDependency = dependencies.find(
		(dependency) => dependency.id === exploringDependencyId,
	);

	try {
		let schemas: SchemaInput[];
		if (exploringDependency?.schemaContent?.trim()) {
			schemas = [
				{
					type: "content",
					content: exploringDependency.schemaContent,
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
	yield* persistExploringDependencySelection(action.payload);
}

function* clearAppliedSelectionWorker() {
	const originalSchema: string = yield select(selectOriginalSchema);
	yield put(setFilteredSchema(originalSchema));
}

function* resetSelectionWorker() {
	const originalSchema: string = yield select(selectOriginalSchema);
	yield put(setFilteredSchema(originalSchema));
	yield* persistExploringDependencySelection("");
}

export function* pruneSchemaSaga() {
	yield takeLatest(pruningStart.type, pruneSchemaWorker);
	yield takeLatest(pruningSuccess.type, pruningSuccessWorker);
	yield takeLatest(clearAppliedSelection.type, clearAppliedSelectionWorker);
	yield takeLatest(resetSelection.type, resetSelectionWorker);
}
