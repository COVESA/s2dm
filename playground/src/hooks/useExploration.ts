import { useEffect } from "react";
import { useConfirmPrompt } from "@/components/ConfirmPromptProvider";
import { selectDependencyDrafts } from "@/store/deps/depsSlice";
import {
	exitExploration,
	selectExploringDependencyId,
	startDependencyExploration,
} from "@/store/exploration/explorationSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { selectOriginalSchema } from "@/store/schema/schemaSlice";
import { selectSelectionQuery } from "@/store/selection/selectionSlice";
import type { DependencyDraft } from "@/types/dependency";

export type ExplorationTarget = {
	kind: "dependency";
	dependency: DependencyDraft;
};

const DISCARD_SELECTION_TITLE = "Discard selection changes?";

/**
 * Explores one dependency at a time. A switch or a stop that would discard unsaved
 * selection changes asks the user first.
 *
 * @returns The explored dependency id and the action that starts, switches or stops exploring.
 */
export function useExploration() {
	const dispatch = useAppDispatch();
	const confirmAction = useConfirmPrompt();
	const exploringDependencyId = useAppSelector(selectExploringDependencyId);
	const dependencies = useAppSelector(selectDependencyDrafts);
	const originalSchema = useAppSelector(selectOriginalSchema);
	const selectionQuery = useAppSelector(selectSelectionQuery);

	const exploredItem = dependencies.find(
		(dependency) => dependency.id === exploringDependencyId,
	);
	const savedSelectionQuery = exploredItem?.selectionContent ?? "";
	const hasUnsavedSelectionChanges = selectionQuery !== savedSelectionQuery;

	const startTarget = (target: ExplorationTarget) => {
		const startAction = startDependencyExploration(target.dependency);
		dispatch(startAction);
	};

	const exitTarget = () => {
		const exitAction = exitExploration();
		dispatch(exitAction);
	};

	const exploreTarget = (target: ExplorationTarget) => {
		if (exploringDependencyId === null) {
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
			confirmLabel: "Switch Dependency",
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
		if (target.dependency.id !== exploringDependencyId) {
			exploreTarget(target);
			return;
		}
		stopExploration();
	};

	useEffect(() => {
		if (exploringDependencyId === null) {
			return;
		}
		if (exploredItem?.schemaContent === originalSchema) {
			return;
		}

		const exitAction = exitExploration();
		dispatch(exitAction);
	}, [dispatch, exploringDependencyId, exploredItem, originalSchema]);

	return {
		exploringDependencyId,
		toggleExploration,
	};
}
