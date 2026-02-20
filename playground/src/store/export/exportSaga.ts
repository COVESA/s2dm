import type { PayloadAction } from "@reduxjs/toolkit";
import { AxiosError } from "axios";
import { call, put, select, takeLatest } from "redux-saga/effects";
import { apiClient } from "@/api/client";
import { mapImportedFilesToSchemaInputs } from "@/api/schemaInputs";
import type { ExportResponse } from "@/api/types";
import { selectExporters } from "@/store/capabilities/capabilitiesSlice";
import {
	type ExportSchemaOptions,
	exportFailure,
	exportSchema as exportSchemaAction,
	exportSuccess,
} from "@/store/export/exportSlice";
import { selectSourceFiles } from "@/store/schema/schemaSlice";
import { selectSelectionQuery } from "@/store/selection/selectionSlice";
import type { ImportedFile } from "@/types/importedFile";

function* exportSchemaWorker(action: PayloadAction<ExportSchemaOptions>) {
	try {
		const { endpoint } = action.payload;
		const sourceFiles: ImportedFile[] = yield select(selectSourceFiles);
		const selectionQuery: string = yield select(selectSelectionQuery);
		const exporters: ReturnType<typeof selectExporters> =
			yield select(selectExporters);

		const exporter = exporters.find((exporter) => exporter.endpoint === endpoint);
		if (!exporter) {
			yield put(exportFailure({ endpoint, error: "Exporter not found" }));
			return;
		}

		const hasSelectionQuery = selectionQuery.trim().length > 0;

		const missingRequired: string[] = [];
		if (exporter.requiresSelectionQuery && !hasSelectionQuery) {
			missingRequired.push("Selection Query");
		}

		for (const [key, property] of Object.entries(exporter.properties)) {
			if (
				property.required &&
				(exporter.propertyValues[key] === null ||
					exporter.propertyValues[key] === undefined)
			) {
				missingRequired.push(property.title || key);
			}
		}

		if (missingRequired.length > 0) {
			yield put(
				exportFailure({
					endpoint,
					error: `Missing required fields: ${missingRequired.join(", ")}`,
				}),
			);
			return;
		}

		const schemas = mapImportedFilesToSchemaInputs(sourceFiles);

		let selectionQueryPayload = null;
		if (hasSelectionQuery) {
			selectionQueryPayload = { type: "content", content: selectionQuery };
		}

		const transformedValues: Record<string, unknown> = {};
		for (const [key, value] of Object.entries(exporter.propertyValues)) {
			const property = exporter.properties[key];

			if (
				property?.type === "contentWrappable" &&
				value !== null &&
				value !== undefined &&
				value !== ""
			) {
				transformedValues[key] = { type: "content", content: value };
			} else {
				transformedValues[key] = value;
			}
		}

		const requestPayload = {
			schemas,
			selection_query: selectionQueryPayload,
			...transformedValues,
		};

		const response: ExportResponse = yield call(
			[apiClient, apiClient.post],
			endpoint,
			requestPayload,
		);

		const output = response.result.join("\n");
		const format = response.metadata?.result_format || "text";

		yield put(exportSuccess({ endpoint, output, format }));
	} catch (err) {
		let errorMsg = "Export failed";

		if (err instanceof AxiosError && err.response?.data?.message) {
			errorMsg = err.response.data.message;
		} else if (err instanceof Error) {
			errorMsg = err.message;
		} else {
			errorMsg = String(err);
		}

		yield put(exportFailure({ endpoint: action.payload.endpoint, error: errorMsg }));
	}
}

export function* exportSaga() {
	yield takeLatest(exportSchemaAction.type, exportSchemaWorker);
}
