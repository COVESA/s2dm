import type { PayloadAction } from "@reduxjs/toolkit";
import { AxiosError } from "axios";
import { call, put, select, takeLatest } from "redux-saga/effects";
import { apiClient } from "@/api/client";
import type { ExportResponse } from "@/api/types";
import type { ImportedFile } from "@/components/FileList";
import { selectExporters } from "@/store/capabilities/capabilitiesSlice";
import {
	type ExportSchemaOptions,
	exportFailure,
	exportSchema as exportSchemaAction,
	exportSuccess,
} from "@/store/export/exportSlice";
import { selectSourceFiles } from "@/store/schema/schemaSlice";
import { selectSelectionQuery } from "@/store/selection/selectionSlice";

function* exportSchemaWorker(action: PayloadAction<ExportSchemaOptions>) {
	try {
		const { endpoint } = action.payload;
		const sourceFiles: ImportedFile[] = yield select(selectSourceFiles);
		const selectionQuery: string = yield select(selectSelectionQuery);
		const exporters: ReturnType<typeof selectExporters> =
			yield select(selectExporters);

		const exporter = exporters.find((exp) => exp.endpoint === endpoint);
		if (!exporter) {
			yield put(exportFailure("Exporter not found"));
			return;
		}

		const missingRequired: string[] = [];
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
				exportFailure(`Missing required fields: ${missingRequired.join(", ")}`),
			);
			return;
		}

		const schemas = sourceFiles.map((file) => {
			if (file.type === "url") {
				return { type: "url", url: file.path };
			}
			return { type: "content", content: file.content! };
		});

		let selectionQueryPayload = null;
		if (selectionQuery) {
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

		yield put(exportSuccess({ output, format }));
	} catch (err) {
		let errorMsg = "Export failed";

		if (err instanceof AxiosError && err.response?.data?.message) {
			errorMsg = err.response.data.message;
		} else if (err instanceof Error) {
			errorMsg = err.message;
		} else {
			errorMsg = String(err);
		}

		yield put(exportFailure(errorMsg));
	}
}

export function* exportSaga() {
	yield takeLatest(exportSchemaAction.type, exportSchemaWorker);
}
