import { call, put, select, takeLatest } from "redux-saga/effects";
import { ApiValidationError, validateSchemas } from "@/api/s2dm";
import { mapImportedFilesToSchemaInputs } from "@/api/schemaInputs";
import type { ExportResponse } from "@/api/types";
import { selectComposedSources } from "@/store/schema/composedSources";
import { setOriginalSchema } from "@/store/schema/schemaSlice";
import {
	validateAndCompose,
	validationFailure,
	validationSuccess,
} from "@/store/validation/validationSlice";
import type { SchemaSource } from "@/types/schemaSource";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* validateAndComposeWorker() {
	const sources: SchemaSource[] = yield select(selectComposedSources);

	if (sources.length === 0) {
		yield put(setOriginalSchema(""));
		yield put(validationSuccess());
		return;
	}

	try {
		const schemas = mapImportedFilesToSchemaInputs(sources);

		const response: ExportResponse = yield call(validateSchemas, schemas);
		const composedSchema = response.result[0] || "";

		yield put(validationSuccess());
		yield put(setOriginalSchema(composedSchema));
	} catch (err) {
		if (err instanceof ApiValidationError) {
			yield put(validationFailure(err.errors));
		} else {
			const errorMsg = getErrorMessage(err);
			yield put(validationFailure([errorMsg]));
		}
		yield put(setOriginalSchema(""));
	}
}

export function* validationSaga() {
	yield takeLatest(validateAndCompose.type, validateAndComposeWorker);
}
