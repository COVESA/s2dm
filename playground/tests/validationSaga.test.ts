import { configureStore } from "@reduxjs/toolkit";
import createSagaMiddleware from "redux-saga";
import { describe, expect, it, vi } from "vitest";
import type { ValidateSchemaResponse } from "@/api/types";
import composeReducer from "@/store/deps/compose/composeSlice";
import schemaReducer, { setSourceFiles } from "@/store/schema/schemaSlice";
import { validationSaga } from "@/store/validation/validationSaga";
import validationReducer, {
	validateAndCompose,
} from "@/store/validation/validationSlice";
import type { ImportedFile } from "@/types/importedFile";

const fakeValidation = vi.hoisted(() => ({
	validateSchemas: vi.fn(),
}));

vi.mock("@/api/s2dm", async (importOriginal) => {
	const originalModule = await importOriginal<typeof import("@/api/s2dm")>();
	return {
		...originalModule,
		validateSchemas: fakeValidation.validateSchemas,
	};
});

function createComposeStore() {
	const sagaMiddleware = createSagaMiddleware();
	const store = configureStore({
		reducer: {
			schema: schemaReducer,
			depsCompose: composeReducer,
			validation: validationReducer,
		},
		middleware: (getDefaultMiddleware) =>
			getDefaultMiddleware().concat(sagaMiddleware),
	});
	sagaMiddleware.run(validationSaga);
	return store;
}

describe("validationSaga", () => {
	it("records the file paths of a successful compose", async () => {
		const response: ValidateSchemaResponse = {
			result: ["type Vehicle { speed: Float }"],
			schema_id: "composed-schema",
		};
		fakeValidation.validateSchemas.mockResolvedValueOnce(response);
		const files: ImportedFile[] = [
			{ name: "a.graphql", path: "spec/a.graphql", type: "file", content: "" },
			{ name: "b.graphql", path: "spec/b.graphql", type: "file", content: "" },
		];
		const store = createComposeStore();
		const filesAction = setSourceFiles(files);
		const composeAction = validateAndCompose();

		store.dispatch(filesAction);
		store.dispatch(composeAction);

		await vi.waitFor(() => {
			const composedFilePaths = store.getState().schema.composedFilePaths;
			expect(composedFilePaths).toEqual(["spec/a.graphql", "spec/b.graphql"]);
		});
	});

	it("clears the composed file paths when a compose fails", async () => {
		const response: ValidateSchemaResponse = {
			result: ["type Vehicle { speed: Float }"],
			schema_id: "composed-schema",
		};
		fakeValidation.validateSchemas
			.mockResolvedValueOnce(response)
			.mockRejectedValueOnce(new Error("compose failed"));
		const files: ImportedFile[] = [
			{ name: "a.graphql", path: "spec/a.graphql", type: "file", content: "" },
		];
		const store = createComposeStore();
		const filesAction = setSourceFiles(files);
		const composeAction = validateAndCompose();

		store.dispatch(filesAction);
		store.dispatch(composeAction);
		await vi.waitFor(() => {
			const composedFilePaths = store.getState().schema.composedFilePaths;
			expect(composedFilePaths).toEqual(["spec/a.graphql"]);
		});
		store.dispatch(composeAction);

		await vi.waitFor(() => {
			const composedFilePaths = store.getState().schema.composedFilePaths;
			expect(composedFilePaths).toEqual([]);
		});
	});
});
