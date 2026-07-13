import type { SchemaInput } from "@/api/types";
import type { SchemaSource } from "@/types/schemaSource";

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
