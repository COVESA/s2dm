import { beforeEach, describe, expect, it } from "vitest";
import {
	selectHasSelection,
	setAppliedSelectionQuery,
	setSelectionQuery,
} from "@/store/selection/selectionSlice";
import { store } from "@/store/store";

describe("selectHasSelection", () => {
	beforeEach(() => {
		const clearQueryAction = setSelectionQuery("");
		const clearAppliedQueryAction = setAppliedSelectionQuery("");
		store.dispatch(clearQueryAction);
		store.dispatch(clearAppliedQueryAction);
	});

	it("is false without a selection query", () => {
		const hasSelection = selectHasSelection(store.getState());

		expect(hasSelection).toBe(false);
	});

	it("is true with a selection query that is not applied", () => {
		const queryAction = setSelectionQuery("query { vehicle }");
		store.dispatch(queryAction);

		const hasSelection = selectHasSelection(store.getState());

		expect(hasSelection).toBe(true);
	});

	it("is true with an applied selection query", () => {
		const appliedQueryAction = setAppliedSelectionQuery("query { vehicle }");
		store.dispatch(appliedQueryAction);

		const hasSelection = selectHasSelection(store.getState());

		expect(hasSelection).toBe(true);
	});
});
