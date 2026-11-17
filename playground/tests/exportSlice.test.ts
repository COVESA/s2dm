import { beforeEach, describe, expect, it } from "vitest";
import {
	clearExportResult,
	exportSuccess,
	selectHasExportResults,
} from "@/store/export/exportSlice";
import { store } from "@/store/store";

describe("selectHasExportResults", () => {
	beforeEach(() => {
		const clearAction = clearExportResult();
		store.dispatch(clearAction);
	});

	it("is false without export results", () => {
		const hasExportResults = selectHasExportResults(store.getState());

		expect(hasExportResults).toBe(false);
	});

	it("is true with an export result", () => {
		const successAction = exportSuccess({
			endpoint: "/api/v1/export/shacl",
			output: "@prefix sh: <http://www.w3.org/ns/shacl#> .",
			format: "turtle",
		});
		store.dispatch(successAction);

		const hasExportResults = selectHasExportResults(store.getState());

		expect(hasExportResults).toBe(true);
	});
});
