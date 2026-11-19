import { describe, expect, it } from "vitest";
import schemaReducer, { setImportError } from "@/store/schema/schemaSlice";

describe("schemaSlice", () => {
	it("keeps the import error until it is cleared", () => {
		const importError = "No GraphQL files found.";
		const errorAction = setImportError(importError);
		const clearAction = setImportError(null);

		const failedState = schemaReducer(undefined, errorAction);
		const clearedState = schemaReducer(failedState, clearAction);

		expect(failedState.importError).toBe(importError);
		expect(clearedState.importError).toBeNull();
	});
});
