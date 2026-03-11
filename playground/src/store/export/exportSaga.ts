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

function getExportErrorMessage(err: unknown): string {
	if (err instanceof AxiosError) {
		if (typeof err.response?.data?.message === "string") {
			return err.response.data.message;
		}

		if (err.code === "ECONNABORTED") {
			return "The API request timed out";
		}

		if (err.code === "ERR_NETWORK") {
			return "Cannot reach the API server";
		}
	}

	if (err instanceof Error) {
		return err.message;
	}

	return String(err);
}

function isEmpty(value: unknown, propertyType: string): boolean {
	if (value === null || value === undefined) {
		return true;
	}

	if (propertyType === "string" || propertyType === "contentWrappable") {
		return typeof value !== "string" || value.trim().length === 0;
	}

	if (
		(propertyType === "integer" || propertyType === "number") &&
		typeof value === "number"
	) {
		return Number.isNaN(value);
	}

	return false;
}

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
			if (property.required && isEmpty(exporter.propertyValues[key], property.type)) {
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
			if (!property || isEmpty(value, property.type)) {
				continue;
			}

			if (property?.type === "contentWrappable") {
				if (value !== null && value !== undefined) {
					transformedValues[key] = {
						type: "content",
						content: typeof value === "string" ? value.trim() : String(value),
					};
					continue;
				}
			}

			transformedValues[key] = value;
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
		const errorMsg = getExportErrorMessage(err);
		yield put(exportFailure({ endpoint: action.payload.endpoint, error: errorMsg }));
	}
}

export function* exportSaga() {
	yield takeLatest(exportSchemaAction.type, exportSchemaWorker);
}
