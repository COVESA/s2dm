import { nanoid } from "@reduxjs/toolkit";

export type DependencyDraft = {
	id: string;
	name: string;
	version: string;
	source: string;
	artifact: string;
	selectionType: "content" | null;
	selectionContent: string | null;
	schemaContent: string | null;
};

export type DependencyEditableField = keyof Pick<
	DependencyDraft,
	"name" | "version" | "source" | "artifact" | "selectionContent"
>;

export const DEPENDENCY_NAME_PATTERN =
	/^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$/;

export function createEmptyDependencyDraft(): DependencyDraft {
	return {
		id: nanoid(),
		name: "",
		version: "",
		source: "",
		artifact: "",
		selectionType: null,
		selectionContent: "",
		schemaContent: null,
	};
}

export function areDependencyDraftsEqual(
	left: DependencyDraft[],
	right: DependencyDraft[],
): boolean {
	if (left.length !== right.length) {
		return false;
	}

	return left.every((leftDraft, index) => {
		const rightDraft = right[index];
		return (
			leftDraft.id === rightDraft.id &&
			leftDraft.name === rightDraft.name &&
			leftDraft.version === rightDraft.version &&
			leftDraft.source === rightDraft.source &&
			leftDraft.artifact === rightDraft.artifact &&
			leftDraft.selectionType === rightDraft.selectionType &&
			leftDraft.selectionContent === rightDraft.selectionContent &&
			leftDraft.schemaContent === rightDraft.schemaContent
		);
	});
}
