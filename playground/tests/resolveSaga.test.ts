import { configureStore } from "@reduxjs/toolkit";
import createSagaMiddleware from "redux-saga";
import { describe, expect, it, vi } from "vitest";
import { depsResolveSaga } from "@/store/deps/resolve/resolveSaga";
import resolveReducer, {
	resolveDependencies,
	setCleanBeforeResolve,
} from "@/store/deps/resolve/resolveSlice";

const fakeResolve = vi.hoisted(() => ({
	resolveDependencies: vi.fn(() => Promise.resolve([])),
}));

vi.mock("@/api/s2dm", async (importOriginal) => {
	const originalModule = await importOriginal<typeof import("@/api/s2dm")>();
	return {
		...originalModule,
		resolveDependencies: fakeResolve.resolveDependencies,
	};
});

describe("depsResolveSaga", () => {
	it("resolves with the stored clean setting", () => {
		const sagaMiddleware = createSagaMiddleware();
		const store = configureStore({
			reducer: { depsResolve: resolveReducer },
			middleware: (getDefaultMiddleware) =>
				getDefaultMiddleware().concat(sagaMiddleware),
		});
		sagaMiddleware.run(depsResolveSaga);
		const cleanAction = setCleanBeforeResolve(true);
		const resolveAction = resolveDependencies();

		store.dispatch(cleanAction);
		store.dispatch(resolveAction);

		expect(fakeResolve.resolveDependencies).toHaveBeenCalledWith(true);
	});
});
