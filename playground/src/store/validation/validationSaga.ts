import { call, put, select, takeLatest } from "redux-saga/effects";
import { ApiValidationError, validateSchemas } from "@/api/s2dm";
import { mapImportedFilesToSchemaInputs } from "@/api/schemaInputs";
import type { SchemaReference, ValidateSchemaResponse } from "@/api/types";
import { selectComposedSources } from "@/store/schema/composedSources";
import {
	setComposedFilePaths,
	setOriginalSchema,
} from "@/store/schema/schemaSlice";
import {
	validateAndCompose,
	validationFailure,
	validationSuccess,
} from "@/store/validation/validationSlice";
import type { ImportedFile } from "@/types/importedFile";
import type { SchemaSource } from "@/types/schemaSource";
import { getErrorMessage } from "@/utils/getErrorMessage";

/**
 * Lists the paths of the imported files among the compose sources.
 *
 * @param sources The sources of one compose.
 * @returns The file paths. The built dependencies content has no path.
 */
function getFilePaths(sources: SchemaSource[]): string[] {
	const files = sources.filter(
		(source): source is ImportedFile => source.type !== "content",
	);
	return files.map((file) => file.path);
}

function* validateAndComposeWorker() {
	const sources: SchemaSource[] = yield select(selectComposedSources);

	if (sources.length === 0) {
		yield put(setOriginalSchema({ schema: "", reference: null }));
		yield put(setComposedFilePaths([]));
		yield put(validationSuccess());
		return;
	}

	try {
		const schemas = mapImportedFilesToSchemaInputs(sources);

		const response: ValidateSchemaResponse = yield call(
			validateSchemas,
			schemas,
		);
		const composedSchema = response.result[0] || "";
		const reference: SchemaReference = {
			type: "schema_id",
			id: response.schema_id,
		};

		const composedFilePaths = getFilePaths(sources);

		yield put(validationSuccess());
		yield put(setOriginalSchema({ schema: composedSchema, reference }));
		yield put(setComposedFilePaths(composedFilePaths));
	} catch (err) {
		if (err instanceof ApiValidationError) {
			yield put(validationFailure(err.errors));
		} else {
			const errorMsg = getErrorMessage(err);
			yield put(validationFailure([errorMsg]));
		}
		yield put(setOriginalSchema({ schema: "", reference: null }));
		yield put(setComposedFilePaths([]));
	}
}

export function* validationSaga() {
	yield takeLatest(validateAndCompose.type, validateAndComposeWorker);
}
