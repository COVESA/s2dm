export type ContentInput = {
	type: "content";
	content: string;
};

export type PathInput = {
	type: "path";
	path: string;
};

type FileContentInput = {
	type: "file_content";
	filename: string;
	content: string;
};

type UrlInput = {
	type: "url";
	url: string;
};

export type SchemaIdInput = {
	type: "schema_id";
	id: string;
};

export type DependencyInput = {
	type: "dependency";
	name: string;
	version: string;
};

export type SchemaReference = SchemaIdInput | DependencyInput;

export type SchemaInput =
	| ContentInput
	| FileContentInput
	| UrlInput
	| SchemaReference;
export type QueryInput = ContentInput;

type SchemasRequest = {
	schemas: SchemaInput[];
};

type SchemasWithSelectionQueryRequest = SchemasRequest & {
	selection_query: QueryInput;
};

export type DependencyConfigEntry = {
	name: string;
	version: string;
	source: string;
	artifact: string;
	selection: ContentInput | PathInput | null;
	schema_content?: string | null;
};

export type DependenciesConfig = {
	dependencies: DependencyConfigEntry[];
};

export type GetDependenciesConfigResponse = DependenciesConfig;

export type SaveDependenciesConfigRequest = DependenciesConfig & {
	config_directory?: string | null;
};

export type DependencyIdentityEntry = {
	host: string;
	scope: string | null;
	token: string;
};

export type DependenciesIdentities = {
	identities: DependencyIdentityEntry[];
};

export type DependencyStatus =
	| "not_configured"
	| "unresolved"
	| "resolved"
	| "invalid";

export type DependenciesStatusResponse = {
	status: DependencyStatus;
};

export type ReleaseAsset = {
	name: string;
	size: number;
};

export type ReleaseSummary = {
	tag: string;
	name: string | null;
	published_at: string | null;
	prerelease: boolean;
	candidate_assets: ReleaseAsset[];
};

export type ReleasePage = {
	releases: ReleaseSummary[];
	page: number;
	has_next: boolean;
	has_previous: boolean;
	last_page: number | null;
};

export type ReleaseMetadata = {
	name: string;
	id: string;
	version: string;
	preferred_prefix: string | null;
};

export type LoadReleaseRequest = {
	repository: string;
	tag: string;
	artifact: string;
};

export type LoadReleaseResponse = {
	schema_content: string;
	schema_id: string;
	metadata: ReleaseMetadata;
};

type ResponseMetadata = {
	result_format: string;
	processing_time_ms?: number;
};

export type ExportResponse = {
	result: string[];
	metadata?: ResponseMetadata;
};

export type ValidateSchemaRequest = SchemasRequest;

type InstanceTagField = {
	dimensions: Record<string, string[]>;
	instances: string[];
};

/** The instance tag fields, by `Type.field`. */
export type InstanceTagsResponse = Partial<Record<string, InstanceTagField>>;

export type ValidateSchemaResponse = ExportResponse & {
	schema_id: string;
};

export type EmbeddingsRequest = SchemasRequest;

export type EmbeddingsBuildResponse = {
	embeddings_id: string;
};

export type EmbeddingsSearchRequest = {
	embeddings_id: string;
	query: string;
	limit: number;
};

export type EmbeddingsSearchHit = {
	rank: number;
	score: number;
	id: string;
};

export type FilterSchemaRequest = SchemasWithSelectionQueryRequest;

export type OpenAPIPath = {
	"x-exporter-name"?: string;
	"x-cli-command-name"?: string;
	requestBody?: {
		content?: {
			"application/json"?: {
				schema?: {
					$ref?: string;
					properties?: Record<string, unknown>;
					required?: string[];
				};
			};
		};
	};
};

export type OpenAPISpec = {
	paths: Record<string, Record<string, OpenAPIPath>>;
	components?: {
		schemas?: Record<string, unknown>;
	};
};

export type SchemaProperty = {
	type: string;
	title?: string;
	description?: string;
	default?: unknown;
	required: boolean;
	format?: string;
	cliFlagName?: string;
	docsUrl?: string;
};

export type ExporterCapability = {
	name: string;
	endpoint: string;
	requiresSelectionQuery: boolean;
	properties: Record<string, SchemaProperty>;
	propertyValues: Record<string, unknown>;
	cliCommandName: string;
};
