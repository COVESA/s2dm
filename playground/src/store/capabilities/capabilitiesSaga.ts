import { call, put, select, takeLatest } from "redux-saga/effects";
import { getCapabilities } from "@/api/capabilities";
import {
	filterExportPaths,
	parseExporters,
	sortExporters,
} from "@/api/parseExporters";
import type { OpenAPISpec } from "@/api/types";
import {
	computeCapabilities,
	computeCapabilitiesSuccess,
	fetchCapabilities,
	fetchCapabilitiesFailure,
	fetchCapabilitiesSuccess,
	selectCapabilitiesSpec,
} from "@/store/capabilities/capabilitiesSlice";

function* fetchCapabilitiesSaga() {
	try {
		const spec: OpenAPISpec = yield call(getCapabilities);
		const filteredSpec = filterExportPaths(spec);

		yield put(fetchCapabilitiesSuccess(filteredSpec));
		yield put(computeCapabilities());
	} catch (err) {
		const errorMsg = err instanceof Error ? err.message : String(err);
		yield put(
			fetchCapabilitiesFailure(
				`Failed to load export capabilities: ${errorMsg}`,
			),
		);
	}
}

function* computeCapabilitiesSaga() {
	try {
		const spec: OpenAPISpec | null = yield select(selectCapabilitiesSpec);

		if (!spec) {
			yield put(
				fetchCapabilitiesFailure(
					"Failed to load export capabilities: No spec available",
				),
			);
			return;
		}

		const exporters = parseExporters(spec);
		const sortedExporters = sortExporters(exporters);

		yield put(computeCapabilitiesSuccess(sortedExporters));
	} catch (err) {
		const errorMsg = err instanceof Error ? err.message : String(err);
		yield put(
			fetchCapabilitiesFailure(
				`Failed to load export capabilities: ${errorMsg}`,
			),
		);
	}
}

export function* capabilitiesSaga() {
	yield takeLatest(fetchCapabilities.type, fetchCapabilitiesSaga);
	yield takeLatest(computeCapabilities.type, computeCapabilitiesSaga);
}
