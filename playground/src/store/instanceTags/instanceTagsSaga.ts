import type { PayloadAction } from "@reduxjs/toolkit";
import { call, put, takeLatest } from "redux-saga/effects";
import { getInstanceTags } from "@/api/s2dm";
import { composedSchemaInputs } from "@/api/schemaInputs";
import type { InstanceTagsResponse } from "@/api/types";
import {
	fetchInstanceTagsFailure,
	fetchInstanceTagsSuccess,
} from "@/store/instanceTags/instanceTagsSlice";
import {
	type OriginalSchemaPayload,
	setOriginalSchema,
} from "@/store/schema/schemaSlice";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* fetchInstanceTagsWorker(
	action: PayloadAction<OriginalSchemaPayload>,
) {
	const { schema: composedSchema, reference } = action.payload;
	if (!composedSchema.trim()) {
		return;
	}

	try {
		const schemas = composedSchemaInputs(composedSchema, reference);
		const response: InstanceTagsResponse = yield call(getInstanceTags, schemas);
		yield put(fetchInstanceTagsSuccess(response));
	} catch (error) {
		const errorMessage = getErrorMessage(error);
		yield put(fetchInstanceTagsFailure(errorMessage));
	}
}

export function* instanceTagsSaga() {
	yield takeLatest(setOriginalSchema.type, fetchInstanceTagsWorker);
}
