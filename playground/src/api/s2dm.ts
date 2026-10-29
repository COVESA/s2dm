import type { ConceptsResponse } from "@insights-ui/types/concepts";
import type { CoverageResponse } from "@insights-ui/types/coverage";
import type { QualityResponse } from "@insights-ui/types/quality";
import type { RelationshipsResponse } from "@insights-ui/types/relationships";
import { AxiosError } from "axios";
import { apiClient } from "@/api/client";
import type {
	DependenciesIdentities,
	DependenciesStatusResponse,
	ExportResponse,
	FilterSchemaRequest,
	GetDependenciesConfigResponse,
	QueryInput,
	SaveDependenciesConfigRequest,
	SchemaInput,
	ValidateSchemaRequest,
} from "@/api/types";
import { getAxiosErrorMessage } from "@/utils/getErrorMessage";

type DependenciesWarningsResponse = {
	warnings: string[];
};

export class ApiValidationError extends Error {
	public errors: string[];

	constructor(message: string, errors: string[]) {
		super(message);
		this.name = "ApiValidationError";
		this.errors = errors;
	}
}

function handleApiError(error: unknown): never {
	const axiosMessage = getAxiosErrorMessage(error);
	if (axiosMessage) {
		throw new Error(axiosMessage);
	}

	if (error instanceof Error && error.message.trim().length > 0) {
		throw new Error(error.message);
	}

	throw new Error("We couldn't complete that request. Please try again.");
}

function isNotFoundError(error: unknown): boolean {
	return error instanceof AxiosError && error.response?.status === 404;
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

export async function getDependenciesConfig(): Promise<GetDependenciesConfigResponse> {
	try {
		return await apiClient.get<GetDependenciesConfigResponse>(
			"/api/v1/deps/config",
		);
	} catch (error) {
		if (isNotFoundError(error)) {
			return { dependencies: [] };
		}

		return handleApiError(error);
	}
}

export async function saveDependenciesConfig(
	config: SaveDependenciesConfigRequest,
): Promise<void> {
	try {
		await apiClient.post<void>("/api/v1/deps/config", config);
	} catch (error) {
		return handleApiError(error);
	}
}

export async function getDependenciesIdentities(): Promise<DependenciesIdentities> {
	try {
		return await apiClient.get<DependenciesIdentities>(
			"/api/v1/deps/identities",
		);
	} catch (error) {
		if (isNotFoundError(error)) {
			return { identities: [] };
		}

		return handleApiError(error);
	}
}

export async function saveDependenciesIdentities(
	identities: DependenciesIdentities,
): Promise<void> {
	try {
		await apiClient.post<void>("/api/v1/deps/identities", identities);
	} catch (error) {
		return handleApiError(error);
	}
}

export async function getDependenciesStatus(): Promise<DependenciesStatusResponse> {
	try {
		return await apiClient.get<DependenciesStatusResponse>(
			"/api/v1/deps/status",
		);
	} catch (error) {
		return handleApiError(error);
	}
}

export async function resolveDependencies(clean: boolean): Promise<string[]> {
	try {
		const response = await apiClient.post<
			DependenciesWarningsResponse | undefined
		>("/api/v1/deps/resolve", { clean });

		if (
			response &&
			typeof response === "object" &&
			"warnings" in response &&
			Array.isArray(response.warnings)
		) {
			return response.warnings;
		}

		return [];
	} catch (error) {
		return handleApiError(error);
	}
}

export async function composeDependencies(
	autoPrefix: boolean,
	preserveQueryType: boolean,
): Promise<string> {
	try {
		const response = await apiClient.post<ExportResponse>(
			"/api/v1/deps/build",
			{
				auto_prefix: autoPrefix,
				preserve_query_type: preserveQueryType,
			},
		);
		return response.result[0] ?? "";
	} catch (error) {
		return handleApiError(error);
	}
}

async function postInsights<TResponse>(
	endpoint: string,
	schemas: SchemaInput[],
): Promise<TResponse> {
	try {
		const request: ValidateSchemaRequest = { schemas };
		return await apiClient.post<TResponse>(endpoint, request);
	} catch (error) {
		return handleApiError(error);
	}
}

export async function getSchemaConcepts(
	schemas: SchemaInput[],
): Promise<ConceptsResponse> {
	return postInsights<ConceptsResponse>("/api/v1/insights/concepts", schemas);
}

export async function getSchemaRelationships(
	schemas: SchemaInput[],
): Promise<RelationshipsResponse> {
	return postInsights<RelationshipsResponse>(
		"/api/v1/insights/relationships",
		schemas,
	);
}

export async function getSchemaCoverage(
	schemas: SchemaInput[],
): Promise<CoverageResponse> {
	return postInsights<CoverageResponse>("/api/v1/insights/coverage", schemas);
}

export async function getSchemaQualityIssues(
	schemas: SchemaInput[],
): Promise<QualityResponse> {
	return postInsights<QualityResponse>("/api/v1/insights/quality", schemas);
}
