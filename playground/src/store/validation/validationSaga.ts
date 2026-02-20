import type { PayloadAction } from "@reduxjs/toolkit";
import { call, put, takeLatest } from "redux-saga/effects";
import { mapImportedFilesToSchemaInputs } from "@/api/schemaInputs";
import { ApiValidationError, validateSchemas } from "@/api/s2dm";
import type { ExportResponse } from "@/api/types";
import { setOriginalSchema, setSourceFiles } from "@/store/schema/schemaSlice";
import type { ImportedFile } from "@/types/importedFile";
import {
	validateAndCompose,
	validationFailure,
	validationSuccess,
} from "@/store/validation/validationSlice";

function* validateAndComposeWorker(action: PayloadAction<ImportedFile[]>) {
	const files = action.payload;

	if (files.length === 0) {
		yield put(setOriginalSchema(""));
		yield put(setSourceFiles([]));
		yield put(validationSuccess());
		return;
	}

	try {
		const schemas = mapImportedFilesToSchemaInputs(files);

		const response: ExportResponse = yield call(validateSchemas, schemas);
		const composedSchema = response.result[0] || "";

		yield put(setSourceFiles(files));
		yield put(validationSuccess());
		yield put(setOriginalSchema(composedSchema));
	} catch (err) {
		if (err instanceof ApiValidationError) {
			yield put(validationFailure(err.errors));
		} else {
			const errorMsg = err instanceof Error ? err.message : String(err);
			yield put(validationFailure([errorMsg]));
		}
		yield put(setOriginalSchema(""));
	}
}

export function* validationSaga() {
	yield takeLatest(validateAndCompose.type, validateAndComposeWorker);
}
