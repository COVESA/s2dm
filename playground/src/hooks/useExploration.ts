import { useEffect } from "react";
import { useConfirmPrompt } from "@/components/ConfirmPromptProvider";
import { selectDependencyDrafts } from "@/store/deps/depsSlice";
import {
	exitExploration,
	selectExploringDependencyId,
	selectExploringReleaseId,
	startDependencyExploration,
	startReleaseExploration,
} from "@/store/exploration/explorationSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { selectLoadedReleases } from "@/store/releases/releasesSlice";
import { selectOriginalSchema } from "@/store/schema/schemaSlice";
import { selectSelectionQuery } from "@/store/selection/selectionSlice";
import type { DependencyDraft } from "@/types/dependency";
import type { LoadedRelease } from "@/types/release";

export type ExplorationTarget =
	| { kind: "dependency"; dependency: DependencyDraft }
	| { kind: "release"; release: LoadedRelease };

type ExploredItem = {
	schemaContent: string | null;
	selectionContent: string | null;
};

const DISCARD_SELECTION_TITLE = "Discard selection changes?";

const SWITCH_LABELS: Record<ExplorationTarget["kind"], string> = {
	dependency: "Switch Dependency",
	release: "Switch Release",
};

function getTargetId(target: ExplorationTarget): string {
	if (target.kind === "dependency") {
		return target.dependency.id;
	}
	return target.release.id;
}

/**
 * Explores one dependency or release at a time. A switch or a stop that would discard unsaved
 * selection changes asks the user first.
 *
 * @returns The explored ids and the actions that start, switch or stop exploring.
 */
export function useExploration() {
	const dispatch = useAppDispatch();
	const confirmAction = useConfirmPrompt();
	const exploringDependencyId = useAppSelector(selectExploringDependencyId);
	const exploringReleaseId = useAppSelector(selectExploringReleaseId);
	const dependencies = useAppSelector(selectDependencyDrafts);
	const loadedReleases = useAppSelector(selectLoadedReleases);
	const originalSchema = useAppSelector(selectOriginalSchema);
	const selectionQuery = useAppSelector(selectSelectionQuery);

	const exploredId = exploringDependencyId ?? exploringReleaseId;
	let exploredItem: ExploredItem | undefined;
	if (exploringDependencyId !== null) {
		exploredItem = dependencies.find(
			(dependency) => dependency.id === exploringDependencyId,
		);
	}
	if (exploringReleaseId !== null) {
		exploredItem = loadedReleases.find(
			(loadedRelease) => loadedRelease.id === exploringReleaseId,
		);
	}
	const savedSelectionQuery = exploredItem?.selectionContent ?? "";
	const hasUnsavedSelectionChanges = selectionQuery !== savedSelectionQuery;

	const startTarget = (target: ExplorationTarget) => {
		if (target.kind === "dependency") {
			const startAction = startDependencyExploration(target.dependency);
			dispatch(startAction);
			return;
		}
		const startAction = startReleaseExploration(target.release);
		dispatch(startAction);
	};

	const exitTarget = () => {
		const exitAction = exitExploration();
		dispatch(exitAction);
	};

	const exploreTarget = (target: ExplorationTarget) => {
		const targetId = getTargetId(target);
		if (targetId === exploredId) {
			return;
		}
		if (exploredId === null) {
			startTarget(target);
			return;
		}
		if (!exploredItem) {
			return;
		}

		confirmAction({
			isDataLost: hasUnsavedSelectionChanges,
			title: DISCARD_SELECTION_TITLE,
			description: `You have unsaved selection query changes. Switch to a different ${target.kind} and discard them?`,
			confirmLabel: SWITCH_LABELS[target.kind],
			onConfirm: () => startTarget(target),
		});
	};

	const stopExploration = () => {
		confirmAction({
			isDataLost: hasUnsavedSelectionChanges,
			title: DISCARD_SELECTION_TITLE,
			description:
				"You have unsaved selection query changes. Exit exploration mode and discard them?",
			confirmLabel: "Exit Exploration",
			onConfirm: exitTarget,
		});
	};

	const toggleExploration = (target: ExplorationTarget) => {
		const targetId = getTargetId(target);
		if (targetId !== exploredId) {
			exploreTarget(target);
			return;
		}
		stopExploration();
	};

	useEffect(() => {
		if (exploredId === null) {
			return;
		}
		if (exploredItem?.schemaContent === originalSchema) {
			return;
		}

		const exitAction = exitExploration();
		dispatch(exitAction);
	}, [dispatch, exploredId, exploredItem, originalSchema]);

	return {
		exploringDependencyId,
		exploringReleaseId,
		toggleExploration,
		exploreTarget,
		stopExploration,
	};
}
