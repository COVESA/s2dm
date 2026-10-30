import type { PayloadAction } from "@reduxjs/toolkit";
import { call, put, takeLatest } from "redux-saga/effects";
import { getInstanceTags } from "@/api/s2dm";
import type { InstanceTagsResponse, SchemaInput } from "@/api/types";
import {
	fetchInstanceTagsFailure,
	fetchInstanceTagsSuccess,
} from "@/store/instanceTags/instanceTagsSlice";
import { setOriginalSchema } from "@/store/schema/schemaSlice";
import { getErrorMessage } from "@/utils/getErrorMessage";

function* fetchInstanceTagsWorker(action: PayloadAction<string>) {
	const schemaContent = action.payload;
	if (!schemaContent.trim()) {
		return;
	}

	try {
		const schemas: SchemaInput[] = [{ type: "content", content: schemaContent }];
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
