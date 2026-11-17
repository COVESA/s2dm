import type { PayloadAction } from "@reduxjs/toolkit";
import type { SagaIterator } from "redux-saga";
import { put, select, takeLatest } from "redux-saga/effects";
import type { SchemaReference } from "@/api/types";
import {
	type ExplorationSnapshot,
	exitExploration,
	selectExplorationSnapshot,
	setExplorationSnapshot,
	startDependencyExploration,
	startReleaseExploration,
} from "@/store/exploration/explorationSlice";
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
import type { LoadedRelease } from "@/types/release";

/**
 * Makes a schema the current schema, with its saved selection query. It clears the applied
 * selection and the validation errors, and it collapses the result pane. When no snapshot
 * exists, it first saves the current schema and selection in one.
 *
 * @param schema The schema text to explore.
 * @param reference The reference to `schema`.
 * @param savedSelectionQuery The saved selection of the explored schema.
 */
function* enterExploration(
	schema: string,
	reference: SchemaReference,
	savedSelectionQuery: string,
): SagaIterator {
	const existingSnapshot: ExplorationSnapshot | null = yield select(
		selectExplorationSnapshot,
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
			setExplorationSnapshot({
				originalSchema,
				originalSchemaReference,
				filteredSchema,
				selectionQuery,
				appliedSelectionQuery,
			}),
		);
	}

	yield put(clearValidationErrors());
	const originalSchemaAction = setOriginalSchema({ schema, reference });
	yield put(originalSchemaAction);
	const selectionQueryAction = setSelectionQuery(savedSelectionQuery);
	yield put(selectionQueryAction);
	yield put(setAppliedSelectionQuery(""));
}

function* startDependencyExplorationWorker(
	action: PayloadAction<DependencyDraft>,
) {
	const dependency = action.payload;
	if (!dependency.schemaContent) {
		return;
	}

	// TODO: build this from the name and version the server sent with `schemaContent`, not the
	// editable draft: an unsaved name or version edit makes it name a different dependency.
	const dependencyReference: SchemaReference = {
		type: "dependency",
		name: dependency.name,
		version: dependency.version,
	};
	const savedSelectionQuery = dependency.selectionContent ?? "";
	yield* enterExploration(
		dependency.schemaContent,
		dependencyReference,
		savedSelectionQuery,
	);
}

function* startReleaseExplorationWorker(action: PayloadAction<LoadedRelease>) {
	const release = action.payload;
	const releaseReference: SchemaReference = {
		type: "schema_id",
		id: release.schemaId,
	};
	yield* enterExploration(
		release.schemaContent,
		releaseReference,
		release.selectionContent,
	);
}

function* exitExplorationWorker() {
	const snapshot: ExplorationSnapshot | null = yield select(
		selectExplorationSnapshot,
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
	yield put(setExplorationSnapshot(null));
}

export function* explorationSaga() {
	yield takeLatest(
		startDependencyExploration.type,
		startDependencyExplorationWorker,
	);
	yield takeLatest(startReleaseExploration.type, startReleaseExplorationWorker);
	yield takeLatest(exitExploration.type, exitExplorationWorker);
}
