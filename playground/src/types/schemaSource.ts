import type { ImportedFile } from "@/types/importedFile";

export type Content = {
	type: "content";
	content: string;
};

export type SchemaSource = ImportedFile | Content;
