type ContentInput = {
	type: "content";
	content: string;
};

type UrlInput = {
	type: "url";
	url: string;
};

export type SchemaInput = ContentInput | UrlInput;
export type QueryInput = ContentInput;

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
};

export type ExporterCapability = {
	name: string;
	endpoint: string;
	properties: Record<string, SchemaProperty>;
	propertyValues: Record<string, unknown>;
	cliCommandName: string;
};
