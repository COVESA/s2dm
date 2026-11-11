import { isDeepStrictEqual } from "node:util";
import { delay, HttpResponse, http } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, expect, test, vi } from "vitest";
import {
	buildEmbeddings,
	composeDependencies,
	getDependenciesConfig,
	getDependenciesIdentities,
	resolveDependencies,
	saveDependenciesConfig,
	validateSchemas,
} from "@/api/s2dm";
import type {
	EmbeddingsBuildResponse,
	ExportResponse,
	GetDependenciesConfigResponse,
	OpenAPISpec,
	SaveDependenciesConfigRequest,
	SchemaInput,
	ValidateSchemaResponse,
} from "@/api/types";
import {
	fetchCapabilities,
	selectExporters,
} from "@/store/capabilities/capabilitiesSlice";
import { exportSchema, selectExportError } from "@/store/export/exportSlice";
import { store } from "@/store/store";

type ApiErrorReply = {
	error: string;
	message: string;
	details: Record<string, unknown> | null;
};

const testApiConfig = vi.hoisted(() => ({
	baseUrl: "http://s2dm.covesa.test",
	timeoutMs: 50,
}));

vi.mock("@/config/api", async (importOriginal) => {
	const actualConfig = await importOriginal<typeof import("@/config/api")>();
	return {
		...actualConfig,
		API_BASE_URL: testApiConfig.baseUrl,
		API_TIMEOUT: testApiConfig.timeoutMs,
	};
});

const VALIDATE_SCHEMAS_URL = `${testApiConfig.baseUrl}/api/v1/schema/validate`;
const DEPENDENCIES_CONFIG_URL = `${testApiConfig.baseUrl}/api/v1/deps/config`;
const DEPENDENCIES_IDENTITIES_URL = `${testApiConfig.baseUrl}/api/v1/deps/identities`;
const BUILD_EMBEDDINGS_URL = `${testApiConfig.baseUrl}/api/v1/embeddings/build`;
const RESOLVE_DEPENDENCIES_URL = `${testApiConfig.baseUrl}/api/v1/deps/resolve`;
const COMPOSE_DEPENDENCIES_URL = `${testApiConfig.baseUrl}/api/v1/deps/build`;
const CAPABILITIES_URL = `${testApiConfig.baseUrl}/api/v1/capabilities`;
/** A reply delay in milliseconds that exceeds the default request timeout. */
const SLOW_REPLY_DELAY_MS = 200;

const schemas: SchemaInput[] = [
	{ type: "content", content: "type Vehicle { speed: Float }" },
];

const server = setupServer();

beforeAll(() => {
	server.listen({ onUnhandledFrame: "error" });
});

afterEach(() => {
	server.resetHandlers();
});

afterAll(() => {
	server.close();
});

test("schema validation sends the schemas as JSON and returns the API's reply", async () => {
	const reply: ValidateSchemaResponse = {
		result: ["type Vehicle { speed: Float }"],
		schema_id: "schema-1",
	};
	const validationHandler = http.post(
		VALIDATE_SCHEMAS_URL,
		async ({ request }) => {
			const contentType = request.headers.get("content-type");
			const body = await request.json();
			const isExpectedRequest =
				contentType === "application/json" &&
				isDeepStrictEqual(body, { schemas });
			if (!isExpectedRequest) {
				const badRequestReply: ApiErrorReply = {
					error: "BadRequest",
					message: "Request contains missing fields or incorrect types",
					details: { validation_errors: [] },
				};
				return HttpResponse.json(badRequestReply, { status: 400 });
			}

			return HttpResponse.json(reply);
		},
	);
	server.use(validationHandler);

	const validation = await validateSchemas(schemas);

	expect(validation).toEqual(reply);
});

test("the dependency config returns the API's reply", async () => {
	const reply: GetDependenciesConfigResponse = {
		dependencies: [
			{
				name: "vehicle",
				version: "1.0.0",
				source: "registry",
				artifact: "schema.graphql",
				selection: null,
			},
		],
	};
	const configHandler = http.get(DEPENDENCIES_CONFIG_URL, () =>
		HttpResponse.json(reply),
	);
	server.use(configHandler);

	const config = await getDependenciesConfig();

	expect(config).toEqual(reply);
});

test("a missing dependency config reads as an empty config", async () => {
	const notFoundReply: ApiErrorReply = {
		error: "NotFound",
		message: "Dependency config is not stored",
		details: null,
	};
	const missingConfigHandler = http.get(DEPENDENCIES_CONFIG_URL, () =>
		HttpResponse.json(notFoundReply, { status: 404 }),
	);
	server.use(missingConfigHandler);

	const config = await getDependenciesConfig();

	expect(config).toEqual({ dependencies: [] });
});

test("missing dependency identities read as an empty list", async () => {
	const notFoundReply: ApiErrorReply = {
		error: "NotFound",
		message: "Dependency identities are not stored",
		details: null,
	};
	const missingIdentitiesHandler = http.get(DEPENDENCIES_IDENTITIES_URL, () =>
		HttpResponse.json(notFoundReply, { status: 404 }),
	);
	server.use(missingIdentitiesHandler);

	const identities = await getDependenciesIdentities();

	expect(identities).toEqual({ identities: [] });
});

test("an error reply shows the API's message", async () => {
	const syntaxErrorReply: ApiErrorReply = {
		error: "GraphQLSyntaxError",
		message: "Syntax Error: Expected Name, found <EOF>.",
		details: null,
	};
	const rejectingValidationHandler = http.post(VALIDATE_SCHEMAS_URL, () =>
		HttpResponse.json(syntaxErrorReply, { status: 422 }),
	);
	server.use(rejectingValidationHandler);

	const validation = validateSchemas(schemas);

	await expect(validation).rejects.toHaveProperty(
		"message",
		syntaxErrorReply.message,
	);
});

test("a reply slower than the timeout shows a timeout message", async () => {
	const slowValidationHandler = http.post(VALIDATE_SCHEMAS_URL, async () => {
		await delay(SLOW_REPLY_DELAY_MS);
		return HttpResponse.json({});
	});
	server.use(slowValidationHandler);

	const validation = validateSchemas(schemas);

	await expect(validation).rejects.toHaveProperty(
		"message",
		"The API request timed out",
	);
});

test("an unreachable API shows a connection message", async () => {
	const unreachableHandler = http.post(VALIDATE_SCHEMAS_URL, () =>
		HttpResponse.error(),
	);
	server.use(unreachableHandler);

	const validation = validateSchemas(schemas);

	await expect(validation).rejects.toHaveProperty(
		"message",
		"Cannot reach the API server",
	);
});

test("an error reply without a message shows a generic message", async () => {
	const badGatewayHandler = http.post(
		VALIDATE_SCHEMAS_URL,
		() => new HttpResponse("Bad Gateway", { status: 502 }),
	);
	server.use(badGatewayHandler);

	const validation = validateSchemas(schemas);

	await expect(validation).rejects.toHaveProperty(
		"message",
		"We couldn't complete that request. Please try again.",
	);
});

test("building embeddings waits for a reply slower than the default timeout", async () => {
	const reply: EmbeddingsBuildResponse = { embeddings_id: "embeddings-1" };
	const slowEmbeddingsHandler = http.post(BUILD_EMBEDDINGS_URL, async () => {
		await delay(SLOW_REPLY_DELAY_MS);
		return HttpResponse.json(reply);
	});
	server.use(slowEmbeddingsHandler);

	const embeddingsId = await buildEmbeddings(schemas);

	expect(embeddingsId).toBe("embeddings-1");
});

test("saving the dependency config accepts a reply without a body", async () => {
	const config: SaveDependenciesConfigRequest = { dependencies: [] };
	const savedConfigHandler = http.post(
		DEPENDENCIES_CONFIG_URL,
		() => new HttpResponse(null, { status: 204 }),
	);
	server.use(savedConfigHandler);

	const saving = saveDependenciesConfig(config);

	await expect(saving).resolves.toBeUndefined();
});

test("resolving without warnings returns an empty list", async () => {
	const resolvedHandler = http.post(
		RESOLVE_DEPENDENCIES_URL,
		() => new HttpResponse(null, { status: 204 }),
	);
	server.use(resolvedHandler);

	const warnings = await resolveDependencies(false);

	expect(warnings).toEqual([]);
});

test("resolving with warnings returns the API's warnings", async () => {
	const reply = {
		warnings: ["Dependency 'vehicle' has no selection."],
	};
	const resolvedWithWarningsHandler = http.post(RESOLVE_DEPENDENCIES_URL, () =>
		HttpResponse.json(reply),
	);
	server.use(resolvedWithWarningsHandler);

	const warnings = await resolveDependencies(false);

	expect(warnings).toEqual(reply.warnings);
});

test("composing the dependencies returns the composed schema", async () => {
	const reply: ExportResponse = {
		result: ["type Vehicle { speed: Float }"],
		metadata: { result_format: "graphql" },
	};
	const composedHandler = http.post(COMPOSE_DEPENDENCIES_URL, () =>
		HttpResponse.json(reply),
	);
	server.use(composedHandler);

	const composedSchema = await composeDependencies(false, false);

	expect(composedSchema).toBe("type Vehicle { speed: Float }");
});

test("composing without a result returns an empty schema", async () => {
	const reply = { result: [], metadata: null };
	const emptyComposedHandler = http.post(COMPOSE_DEPENDENCIES_URL, () =>
		HttpResponse.json(reply),
	);
	server.use(emptyComposedHandler);

	const composedSchema = await composeDependencies(false, false);

	expect(composedSchema).toBe("");
});

test("a failed export shows the API's message", async () => {
	const exportPath = "/api/v1/export/shacl";
	const capabilities: OpenAPISpec = {
		paths: {
			[exportPath]: {
				post: { "x-exporter-name": "SHACL", "x-cli-command-name": "shacl" },
			},
		},
	};
	const badRequestReply: ApiErrorReply = {
		error: "BadRequest",
		message: "Request contains missing fields or incorrect types",
		details: { validation_errors: [] },
	};
	const capabilitiesHandler = http.get(CAPABILITIES_URL, () =>
		HttpResponse.json(capabilities),
	);
	const rejectingExportHandler = http.post(
		`${testApiConfig.baseUrl}${exportPath}`,
		() => HttpResponse.json(badRequestReply, { status: 400 }),
	);
	server.use(capabilitiesHandler, rejectingExportHandler);

	store.dispatch(fetchCapabilities());
	await vi.waitFor(() => {
		const exporters = selectExporters(store.getState());
		expect(exporters).toHaveLength(1);
	});
	store.dispatch(exportSchema({ endpoint: exportPath }));

	await vi.waitFor(() => {
		const exportError = selectExportError(store.getState(), exportPath);
		expect(exportError).toBe(badRequestReply.message);
	});
});
