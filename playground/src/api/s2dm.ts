import { AxiosError } from "axios";
import { apiClient } from "@/api/client";
import type {
	ExportResponse,
	FilterSchemaRequest,
	QueryInput,
	SchemaInput,
	ValidateSchemaRequest,
} from "@/api/types";

export class ApiValidationError extends Error {
	public errors: string[];

	constructor(message: string, errors: string[]) {
		super(message);
		this.name = "ApiValidationError";
		this.errors = errors;
	}
}

function handleApiError(error: unknown): never {
	if (error instanceof AxiosError && error.response?.data?.message) {
		throw new Error(error.response.data.message);
	}

	throw new Error("Something went wrong");
}

export async function validateSchemas(
	schemas: SchemaInput[],
): Promise<ExportResponse> {
	try {
		const request: ValidateSchemaRequest = { schemas };
		return await apiClient.post<ExportResponse>(
			"/api/v1/schema/validate",
			request,
		);
	} catch (error) {
		return handleApiError(error);
	}
}

export async function filterSchema(
	schemas: SchemaInput[],
	selectionQuery: QueryInput,
): Promise<ExportResponse> {
	try {
		const request: FilterSchemaRequest = {
			schemas,
			selection_query: selectionQuery,
		};
		return await apiClient.post<ExportResponse>(
			"/api/v1/schema/filter",
			request,
		);
	} catch (error) {
		return handleApiError(error);
	}
}
