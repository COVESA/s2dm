import type { PayloadAction } from "@reduxjs/toolkit";
import { put, select, takeLatest } from "redux-saga/effects";
import {
	type DependencyExplorationSnapshot,
	exitDependencyExploration,
	selectDependencyExplorationSnapshot,
	setDependencyExplorationSnapshot,
	startDependencyExploration,
} from "@/store/deps/dependencyExploration/dependencyExplorationSlice";
import {
	selectFilteredSchema,
	selectOriginalSchema,
	setFilteredSchema,
	setOriginalSchema,
} from "@/store/schema/schemaSlice";
import {
	selectAppliedSelectionQuery,
	selectSelectionQuery,
	setAppliedSelectionQuery,
	setSelectionQuery,
} from "@/store/selection/selectionSlice";
import {
	selectResultPaneCollapsed,
	toggleResultPane,
} from "@/store/ui/uiSlice";
import { clearValidationErrors } from "@/store/validation/validationSlice";
import type { DependencyDraft } from "@/types/dependency";

function* startDependencyExplorationWorker(
	action: PayloadAction<DependencyDraft>,
) {
	const dependency = action.payload;
	if (!dependency.schemaContent) {
		return;
	}

	const existingSnapshot: DependencyExplorationSnapshot | null = yield select(
		selectDependencyExplorationSnapshot,
	);
	const isResultPaneCollapsed: boolean = yield select(
		selectResultPaneCollapsed,
	);

	if (!isResultPaneCollapsed) {
		yield put(toggleResultPane());
	}

	if (!existingSnapshot) {
		const originalSchema: string = yield select(selectOriginalSchema);
		const filteredSchema: string = yield select(selectFilteredSchema);
		const selectionQuery: string = yield select(selectSelectionQuery);
		const appliedSelectionQuery: string = yield select(
			selectAppliedSelectionQuery,
		);

		yield put(
			setDependencyExplorationSnapshot({
				originalSchema,
				filteredSchema,
				selectionQuery,
				appliedSelectionQuery,
			}),
		);
	}

	yield put(clearValidationErrors());
	yield put(setOriginalSchema(dependency.schemaContent));
	yield put(setSelectionQuery(dependency.selectionContent ?? ""));
	yield put(setAppliedSelectionQuery(""));
}

function* exitDependencyExplorationWorker() {
	const snapshot: DependencyExplorationSnapshot | null = yield select(
		selectDependencyExplorationSnapshot,
	);

	if (!snapshot) {
		return;
	}

	yield put(clearValidationErrors());
	yield put(setOriginalSchema(snapshot.originalSchema));
	yield put(setFilteredSchema(snapshot.filteredSchema));
	yield put(setSelectionQuery(snapshot.selectionQuery));
	yield put(setAppliedSelectionQuery(snapshot.appliedSelectionQuery));
	yield put(setDependencyExplorationSnapshot(null));
}

export function* depsExplorationSaga() {
	yield takeLatest(
		startDependencyExploration.type,
		startDependencyExplorationWorker,
	);
	yield takeLatest(
		exitDependencyExploration.type,
		exitDependencyExplorationWorker,
	);
}
