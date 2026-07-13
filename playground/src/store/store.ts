import { configureStore } from "@reduxjs/toolkit";
import createSagaMiddleware from "redux-saga";
import { all } from "redux-saga/effects";
import { appSaga } from "@/store/app/appSaga";
import appReducer from "@/store/app/appSlice";
import { capabilitiesSaga } from "@/store/capabilities/capabilitiesSaga";
import capabilitiesReducer from "@/store/capabilities/capabilitiesSlice";
import { depsComposeSaga } from "@/store/deps/compose/composeSaga";
import depsComposeReducer from "@/store/deps/compose/composeSlice";
import { depsExplorationSaga } from "@/store/deps/dependencyExploration/dependencyExplorationSaga";
import dependencyExplorationReducer from "@/store/deps/dependencyExploration/dependencyExplorationSlice";
import { depsSaga } from "@/store/deps/depsSaga";
import depsReducer from "@/store/deps/depsSlice";
import { depsIdentitiesSaga } from "@/store/deps/identities/identitiesSaga";
import depsIdentitiesReducer from "@/store/deps/identities/identitiesSlice";
import { depsResolveSaga } from "@/store/deps/resolve/resolveSaga";
import depsResolveReducer from "@/store/deps/resolve/resolveSlice";
import { exportSaga } from "@/store/export/exportSaga";
import exportReducer from "@/store/export/exportSlice";
import schemaReducer from "@/store/schema/schemaSlice";
import { pruneSchemaSaga } from "@/store/selection/pruneSchemaSaga";
import selectionReducer from "@/store/selection/selectionSlice";
import type { RootState } from "@/store/types";
import uiReducer from "@/store/ui/uiSlice";
import { validationSaga } from "@/store/validation/validationSaga";
import validationReducer from "@/store/validation/validationSlice";

function* rootSaga() {
	yield all([
		appSaga(),
		depsSaga(),
		depsExplorationSaga(),
		depsIdentitiesSaga(),
		depsResolveSaga(),
		depsComposeSaga(),
		pruneSchemaSaga(),
		validationSaga(),
		exportSaga(),
		capabilitiesSaga(),
	]);
}

const sagaMiddleware = createSagaMiddleware();

export const store = configureStore({
	reducer: {
		app: appReducer,
		deps: depsReducer,
		dependencyExploration: dependencyExplorationReducer,
		depsIdentities: depsIdentitiesReducer,
		depsResolve: depsResolveReducer,
		depsCompose: depsComposeReducer,
		schema: schemaReducer,
		selection: selectionReducer,
		validation: validationReducer,
		ui: uiReducer,
		schemaExport: exportReducer,
		capabilities: capabilitiesReducer,
	},
	middleware: (getDefaultMiddleware) =>
		getDefaultMiddleware({
			thunk: false,
			serializableCheck: false,
		}).concat(sagaMiddleware),
});

sagaMiddleware.run(rootSaga);

export type { RootState };
export type AppDispatch = typeof store.dispatch;
