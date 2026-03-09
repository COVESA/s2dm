import type { PayloadAction } from "@reduxjs/toolkit";
import { call, put, select, takeLatest } from "redux-saga/effects";
import { mapImportedFilesToSchemaInputs } from "@/api/schemaInputs";
import { ApiValidationError, filterSchema } from "@/api/s2dm";
import type { ExportResponse, QueryInput } from "@/api/types";
import {
	selectSourceFiles,
	setFilteredSchema,
} from "@/store/schema/schemaSlice";
import {
	pruningFailure,
	pruningStart,
	pruningSuccess,
	resetSelectionQuery,
} from "@/store/selection/selectionSlice";
import type { RootState } from "@/store/store";
import type { ImportedFile } from "@/types/importedFile";

function* pruneSchemaWorker(action: PayloadAction<string>) {
	const query = action.payload;

	if (!query || query.trim() === "") {
		return;
	}

	const originalSchema: string = yield select(
		(state: RootState) => state.schema.original,
	);
	const sourceFiles: ImportedFile[] = yield select(selectSourceFiles);

	try {
		const schemas = mapImportedFilesToSchemaInputs(sourceFiles);

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
			errorMsg = err instanceof Error ? err.message : String(err);
		}
		console.error("Failed to prune schema:", err);
		yield put(setFilteredSchema(originalSchema));
		yield put(pruningFailure(errorMsg));
	}
}

function* resetSelectionWorker() {
	const originalSchema: string = yield select(
		(state: RootState) => state.schema.original,
	);
	yield put(setFilteredSchema(originalSchema));
}

export function* pruneSchemaSaga() {
	yield takeLatest(pruningStart.type, pruneSchemaWorker);
	yield takeLatest(resetSelectionQuery.type, resetSelectionWorker);
}
