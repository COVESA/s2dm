import { nanoid } from "@reduxjs/toolkit";

export type DependencyIdentityDraft = {
	id: string;
	host: string;
	scope: string;
	token: string;
};

export type DependencyIdentityEditableField = keyof Pick<
	DependencyIdentityDraft,
	"host" | "scope" | "token"
>;

export function createEmptyDependencyIdentityDraft(): DependencyIdentityDraft {
	return {
		id: nanoid(),
		host: "",
		scope: "",
		token: "",
	};
}

export function areDependencyIdentityDraftsEqual(
	left: DependencyIdentityDraft[],
	right: DependencyIdentityDraft[],
): boolean {
	if (left.length !== right.length) {
		return false;
	}

	return left.every((leftDraft, index) => {
		const rightDraft = right[index];
		return (
			leftDraft.id === rightDraft.id &&
			leftDraft.host === rightDraft.host &&
			leftDraft.scope === rightDraft.scope &&
			leftDraft.token === rightDraft.token
		);
	});
}
