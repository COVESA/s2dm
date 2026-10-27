import type { PayloadAction } from "@reduxjs/toolkit";
import { put, select, takeLatest } from "redux-saga/effects";
import type { SchemaReference } from "@/api/types";
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
	selectOriginalSchemaReference,
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
		const originalSchemaReference: SchemaReference | null = yield select(
			selectOriginalSchemaReference,
		);
		const filteredSchema: string = yield select(selectFilteredSchema);
		const selectionQuery: string = yield select(selectSelectionQuery);
		const appliedSelectionQuery: string = yield select(
			selectAppliedSelectionQuery,
		);

		yield put(
			setDependencyExplorationSnapshot({
				originalSchema,
				originalSchemaReference,
				filteredSchema,
				selectionQuery,
				appliedSelectionQuery,
			}),
		);
	}

	// TODO: build this from the name and version the server sent with `schemaContent`, not the
	// editable draft: an unsaved name or version edit makes it name a different dependency.
	const dependencyReference: SchemaReference = {
		type: "dependency",
		name: dependency.name,
		version: dependency.version,
	};
	yield put(clearValidationErrors());
	yield put(
		setOriginalSchema({
			schema: dependency.schemaContent,
			reference: dependencyReference,
		}),
	);
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
	yield put(
		setOriginalSchema({
			schema: snapshot.originalSchema,
			reference: snapshot.originalSchemaReference,
		}),
	);
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
