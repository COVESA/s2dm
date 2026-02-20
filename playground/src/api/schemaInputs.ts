import type { SchemaInput } from "@/api/types";
import type { ImportedFile } from "@/types/importedFile";

export function mapImportedFilesToSchemaInputs(
	importedFiles: ImportedFile[],
): SchemaInput[] {
	return importedFiles.map((importedFile) => {
		if (importedFile.type === "url") {
			return { type: "url", url: importedFile.path };
		}

		return { type: "content", content: importedFile.content ?? "" };
	});
}
