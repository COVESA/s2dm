import type { ExporterCapability } from "@/api/types";
import {
	FILTERED_SCHEMA_FILENAME,
	ORIGINAL_SCHEMA_FILENAME,
	SELECTION_QUERY_FILENAME,
} from "@/constants";
import type { ImportedFile } from "@/types/importedFile";

export function buildComposeCommand(schemas: ImportedFile[]): string | null {
	if (schemas.length === 0) {
		return null;
	}

	const parts: string[] = ["s2dm compose"];

	for (const schema of schemas) {
		if (schema.type === "file") {
			parts.push(`--schema ${schema.name}`);
		} else if (schema.type === "url") {
			parts.push(`--schema ${schema.path}`);
		}
	}

	return parts.join(" ");
}

function formatValue(
	value: unknown,
	propertyType: string,
	propertyKey: string,
	propertyFormat?: string,
): string {
	if (propertyType === "boolean") {
		return value === true ? "true" : "false";
	}

	if (propertyType === "contentWrappable") {
		const fileExtension = propertyFormat || "txt";
		return `${propertyKey}.${fileExtension}`;
	}

	if (typeof value === "string") {
		return `"${value}"`;
	}

	return String(value);
}

export function buildCliCommand(
	exporter: ExporterCapability,
	schemas: ImportedFile[],
	selectionQuery: string,
	outputFormat?: string,
): string | null {
	if (schemas.length === 0) {
		return null;
	}

	const parts: string[] = [`s2dm export ${exporter.cliCommandName}`];

	const fileSchemas = schemas.filter((schema) => schema.type === "file");
	const urlSchemas = schemas.filter((schema) => schema.type === "url");

	const hasSelectionQuery = selectionQuery.trim().length > 0;
	const schemaFilename = hasSelectionQuery
		? FILTERED_SCHEMA_FILENAME
		: ORIGINAL_SCHEMA_FILENAME;

	if (fileSchemas.length >= 1) {
		parts.push(`--schema ${schemaFilename}`);
	}

	if (urlSchemas.length === 1) {
		parts.push(`--schema ${urlSchemas[0].path}`);
	} else if (urlSchemas.length > 1) {
		parts.push("--schema <urls>");
	}

	if (hasSelectionQuery) {
		parts.push(`--selection-query ${SELECTION_QUERY_FILENAME}`);
	}

	for (const [key, property] of Object.entries(exporter.properties)) {
		if (!property.cliFlagName) {
			continue;
		}

		const value = exporter.propertyValues[key];

		if (value === null || value === undefined || value === "") {
			if (property.required && property.type === "boolean") {
				parts.push(`${property.cliFlagName} false`);
			}
			continue;
		}

		const formattedValue = formatValue(
			value,
			property.type,
			key,
			property.format,
		);
		parts.push(`${property.cliFlagName} ${formattedValue}`);
	}

	if (outputFormat) {
		parts.push(`--output output.${outputFormat}`);
	}

	return parts.join(" ");
}
