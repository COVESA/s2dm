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

export type SchemaInput = ContentInput | FileContentInput | UrlInput;
export type QueryInput = ContentInput;

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

type ResponseMetadata = {
	result_format: string;
	processing_time_ms?: number;
};

export type ExportResponse = {
	result: string[];
	metadata?: ResponseMetadata;
};

export type ValidateSchemaRequest = {
	schemas: SchemaInput[];
};

export type FilterSchemaRequest = {
	schemas: SchemaInput[];
	selection_query: QueryInput;
};

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
