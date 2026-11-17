import { describe, expect, it } from "vitest";
import depsReducer, {
	addDependency,
	discardDependencyChanges,
	fetchDependenciesConfigSuccess,
	updateDependency,
} from "@/store/deps/depsSlice";
import {
	createEmptyDependencyDraft,
	type DependencyDraft,
} from "@/types/dependency";

describe("depsSlice", () => {
	it("discards the unsaved dependency changes", () => {
		const emptyDependency = createEmptyDependencyDraft();
		const storedDependency: DependencyDraft = {
			...emptyDependency,
			name: "base",
			version: "1.0.0",
		};
		const editedDependency: DependencyDraft = {
			...storedDependency,
			version: "2.0.0",
		};
		const addedDependency = createEmptyDependencyDraft();
		const fetchAction = fetchDependenciesConfigSuccess([storedDependency]);
		const updateAction = updateDependency(editedDependency);
		const addAction = addDependency(addedDependency);
		const discardAction = discardDependencyChanges();

		const loadedState = depsReducer(undefined, fetchAction);
		const updatedState = depsReducer(loadedState, updateAction);
		const editedState = depsReducer(updatedState, addAction);
		const discardedState = depsReducer(editedState, discardAction);

		expect(discardedState.dependencies).toEqual([storedDependency]);
	});
});
