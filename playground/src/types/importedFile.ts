export type ImportedFile = {
	name: string;
	path: string;
	type: "file" | "url";
	content?: string;
};
