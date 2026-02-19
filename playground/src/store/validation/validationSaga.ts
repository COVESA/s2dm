import type { PayloadAction } from "@reduxjs/toolkit";
import { call, put, takeLatest } from "redux-saga/effects";
import { ApiValidationError, validateSchemas } from "@/api/s2dm";
import type { ExportResponse, SchemaInput } from "@/api/types";
import type { ImportedFile } from "@/components/FileList";
import { setOriginalSchema, setSourceFiles } from "@/store/schema/schemaSlice";
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
		const schemas: SchemaInput[] = files.map((file) => {
			if (file.type === "url") {
				return { type: "url", url: file.path };
			}
			return { type: "content", content: file.content || "" };
		});

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
