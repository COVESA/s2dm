import type { SchemaInput, SchemaReference } from "@/api/types";
import type { SchemaSource } from "@/types/schemaSource";

/**
 * Build the request inputs for a composed schema. Prefer the reference, so the request does
 * not resend the schema text.
 *
 * @param schema The composed schema text. Sent only when there is no reference.
 * @param reference The reference to `schema` itself, or null. A filtered schema has no reference.
 * @returns A single input: the reference, or else the text.
 */
export function composedSchemaInputs(
	schema: string,
	reference: SchemaReference | null,
): SchemaInput[] {
	if (reference) {
		return [reference];
	}
	return [{ type: "content", content: schema }];
}

export function mapImportedFilesToSchemaInputs(
	sources: SchemaSource[],
): SchemaInput[] {
	return sources.map((source) => {
		if (source.type === "content") {
			return { type: "content", content: source.content };
		}

		if (source.type === "url") {
			return { type: "url", url: source.path };
		}

		const content = source.content ?? "";
		if (source.name.trim()) {
			return {
				type: "file_content",
				filename: source.name,
				content,
			};
		}

		return { type: "content", content };
	});
}
