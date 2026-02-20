import { apiClient } from "@/api/client";
import type { OpenAPISpec } from "@/api/types";

export async function getCapabilities(): Promise<OpenAPISpec> {
	return await apiClient.get<OpenAPISpec>("/api/v1/capabilities");
}
