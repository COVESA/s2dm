import type {
	ExporterCapability,
	OpenAPIPath,
	OpenAPISpec,
	SchemaProperty,
} from "@/api/types";

function resolveSchemaRef(
	ref: string,
	spec: OpenAPISpec,
): Record<string, unknown> | null {
	if (!ref.startsWith("#/components/schemas/")) {
		return null;
	}

	const schemaName = ref.replace("#/components/schemas/", "");
	const schema = spec.components?.schemas?.[schemaName];

	if (!schema || typeof schema !== "object") {
		return null;
	}

	return schema as Record<string, unknown>;
}

function extractPrimitiveFromAnyOf(anyOf: unknown): string | null {
	if (!Array.isArray(anyOf)) {
		return null;
	}

	let foundPrimitiveType: string | null = null;

	for (const anyOfOption of anyOf) {
		if (typeof anyOfOption !== "object" || anyOfOption === null) {
			continue;
		}

		const anyOfTypeDefinition = anyOfOption as Record<string, unknown>;

		if (anyOfTypeDefinition.$ref) {
			return null;
		}

		if (
			anyOfTypeDefinition.type === "string" ||
			anyOfTypeDefinition.type === "boolean" ||
			anyOfTypeDefinition.type === "integer" ||
			anyOfTypeDefinition.type === "number"
		) {
			if (!foundPrimitiveType) {
				foundPrimitiveType = anyOfTypeDefinition.type;
			}
		}
	}

	return foundPrimitiveType;
}

function detectContentInputWrapper(anyOf: unknown, spec: OpenAPISpec): boolean {
	if (!Array.isArray(anyOf)) {
		return false;
	}

	for (const anyOfOption of anyOf) {
		if (typeof anyOfOption !== "object" || anyOfOption === null) {
			continue;
		}

		const anyOfTypeDefinition = anyOfOption as Record<string, unknown>;

		if (!anyOfTypeDefinition.$ref) {
			continue;
		}

		const resolvedSchema = resolveSchemaRef(
			anyOfTypeDefinition.$ref as string,
			spec,
		);

		if (!resolvedSchema) {
			continue;
		}

		const properties = resolvedSchema.properties as
			| Record<string, unknown>
			| undefined;

		if (!properties) {
			continue;
		}

		const typeProperty = properties.type as Record<string, unknown> | undefined;
		const hasContentField = "content" in properties;

		if (typeProperty?.const === "content" && hasContentField) {
			return true;
		}
	}

	return false;
}

function extractProperties(
	schema: Record<string, unknown>,
	spec: OpenAPISpec,
): Record<string, SchemaProperty> {
	const properties: Record<string, SchemaProperty> = {};

	const schemaProps = schema.properties as Record<string, unknown> | undefined;
	const requiredFields = (schema.required as string[]) || [];

	if (!schemaProps || typeof schemaProps !== "object") {
		return properties;
	}

	for (const [propName, propDef] of Object.entries(schemaProps)) {
		if (propName === "schemas" || propName === "selection_query") {
			continue;
		}

		if (typeof propDef !== "object" || propDef === null) {
			continue;
		}

		const propObj = propDef as Record<string, unknown>;

		let propertyType: string | null = null;

		if (propObj.anyOf) {
			if (detectContentInputWrapper(propObj.anyOf, spec)) {
				propertyType = "contentWrappable";
			} else {
				propertyType = extractPrimitiveFromAnyOf(propObj.anyOf);
			}
		} else if (typeof propObj.type === "string") {
			propertyType = propObj.type;
		}

		if (!propertyType) {
			continue;
		}

		properties[propName] = {
			type: propertyType,
			title: typeof propObj.title === "string" ? propObj.title : undefined,
			description:
				typeof propObj.description === "string"
					? propObj.description
					: undefined,
			default: propObj.default,
			required: requiredFields.includes(propName),
			format:
				typeof propObj["x-property-format"] === "string"
					? propObj["x-property-format"]
					: undefined,
			cliFlagName:
				typeof propObj["x-cli-flag"] === "string"
					? propObj["x-cli-flag"]
					: undefined,
		};
	}

	return properties;
}

function isSelectionQueryRequired(schema: Record<string, unknown>): boolean {
	if (!Array.isArray(schema.required)) {
		return false;
	}

	return schema.required.includes("selection_query");
}

export function computePropertyValues(
	properties: Record<string, SchemaProperty>,
): Record<string, unknown> {
	const propertyValues: Record<string, unknown> = {};
	for (const [key, property] of Object.entries(properties)) {
		propertyValues[key] = property.default ?? null;
	}
	return propertyValues;
}

export function filterExportPaths(spec: OpenAPISpec): OpenAPISpec {
	const filteredPaths: Record<string, Record<string, OpenAPIPath>> = {};
	for (const [path, methods] of Object.entries(spec.paths)) {
		if (path.includes("/export/")) {
			filteredPaths[path] = methods;
		}
	}

	return {
		...spec,
		paths: filteredPaths,
	};
}

export function sortExporters(
	exporters: ExporterCapability[],
): ExporterCapability[] {
	return exporters.sort((first, second) =>
		first.name.localeCompare(second.name),
	);
}

export function parseExporters(spec: OpenAPISpec): ExporterCapability[] {
	const exporters: ExporterCapability[] = [];

	for (const [path, methods] of Object.entries(spec.paths)) {
		for (const [method, operation] of Object.entries(methods)) {
			if (method !== "post" || !operation["x-exporter-name"]) {
				continue;
			}

			let properties: Record<string, SchemaProperty> = {};
			let requiresSelectionQuery = false;

			const schemaRef =
				operation.requestBody?.content?.["application/json"]?.schema?.$ref;

			if (schemaRef && typeof schemaRef === "string") {
				const resolvedSchema = resolveSchemaRef(schemaRef, spec);
				if (resolvedSchema) {
					properties = extractProperties(resolvedSchema, spec);
					requiresSelectionQuery = isSelectionQueryRequired(resolvedSchema);
				}
			}

			const propertyValues = computePropertyValues(properties);

			const cliCommandName =
				typeof operation["x-cli-command-name"] === "string"
					? operation["x-cli-command-name"]
					: "";

			exporters.push({
				name: operation["x-exporter-name"],
				endpoint: path,
				requiresSelectionQuery,
				properties,
				propertyValues,
				cliCommandName,
			});
		}
	}

	return exporters;
}
