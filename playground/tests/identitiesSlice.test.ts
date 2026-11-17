import { describe, expect, it } from "vitest";
import identitiesReducer, {
	addIdentity,
	discardIdentityChanges,
	fetchIdentitiesSuccess,
	updateIdentity,
} from "@/store/deps/identities/identitiesSlice";
import {
	createEmptyDependencyIdentityDraft,
	type DependencyIdentityDraft,
} from "@/types/dependencyIdentity";

describe("identitiesSlice", () => {
	it("discards the unsaved identity changes", () => {
		const emptyIdentity = createEmptyDependencyIdentityDraft();
		const storedIdentity: DependencyIdentityDraft = {
			...emptyIdentity,
			host: "github.com",
			token: "stored-token",
		};
		const editedIdentity: DependencyIdentityDraft = {
			...storedIdentity,
			token: "edited-token",
		};
		const addedIdentity = createEmptyDependencyIdentityDraft();
		const fetchAction = fetchIdentitiesSuccess([storedIdentity]);
		const updateAction = updateIdentity(editedIdentity);
		const addAction = addIdentity(addedIdentity);
		const discardAction = discardIdentityChanges();

		const loadedState = identitiesReducer(undefined, fetchAction);
		const updatedState = identitiesReducer(loadedState, updateAction);
		const editedState = identitiesReducer(updatedState, addAction);
		const discardedState = identitiesReducer(editedState, discardAction);

		expect(discardedState.identities).toEqual([storedIdentity]);
	});
});
