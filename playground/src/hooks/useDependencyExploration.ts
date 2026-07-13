import { useCallback, useEffect, useState } from "react";
import {
	exitDependencyExploration,
	selectExploringDependencyId,
	startDependencyExploration,
} from "@/store/deps/dependencyExploration/dependencyExplorationSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { selectOriginalSchema } from "@/store/schema/schemaSlice";
import { selectSelectionQuery } from "@/store/selection/selectionSlice";
import type { DependencyDraft } from "@/types/dependency";

type PendingExplorationAction =
	| { kind: "stop" }
	| { kind: "switch"; dependency: DependencyDraft };

export function useDependencyExploration(dependencies: DependencyDraft[]) {
	const dispatch = useAppDispatch();
	const exploringDependencyId = useAppSelector(selectExploringDependencyId);
	const originalSchema = useAppSelector(selectOriginalSchema);
	const selectionQuery = useAppSelector(selectSelectionQuery);

	const [pendingAction, setPendingAction] =
		useState<PendingExplorationAction | null>(null);

	const toggleExploration = useCallback(
		(dependency: DependencyDraft) => {
			if (exploringDependencyId === null) {
				dispatch(startDependencyExploration(dependency));
				return;
			}

			const activeDependency = dependencies.find(
				(candidate) => candidate.id === exploringDependencyId,
			);
			if (!activeDependency) {
				return;
			}

			const savedSelectionQuery = activeDependency.selectionContent ?? "";
			const hasUnsavedSelectionChanges = selectionQuery !== savedSelectionQuery;
			const isStoppingExploration = exploringDependencyId === dependency.id;

			if (hasUnsavedSelectionChanges) {
				setPendingAction(
					isStoppingExploration
						? { kind: "stop" }
						: { kind: "switch", dependency },
				);
				return;
			}

			if (isStoppingExploration) {
				dispatch(exitDependencyExploration());
				return;
			}

			dispatch(startDependencyExploration(dependency));
		},
		[dependencies, dispatch, exploringDependencyId, selectionQuery],
	);

	useEffect(() => {
		if (!exploringDependencyId) {
			return;
		}

		const activeDependency = dependencies.find(
			(dependency) => dependency.id === exploringDependencyId,
		);
		if (activeDependency?.schemaContent === originalSchema) {
			return;
		}

		dispatch(exitDependencyExploration());
	}, [dependencies, dispatch, exploringDependencyId, originalSchema]);

	const dismissPendingAction = useCallback(() => {
		setPendingAction(null);
	}, []);

	const confirmPendingAction = useCallback(() => {
		if (!pendingAction) {
			return;
		}
		if (pendingAction.kind === "switch") {
			dispatch(startDependencyExploration(pendingAction.dependency));
		} else {
			dispatch(exitDependencyExploration());
		}
		setPendingAction(null);
	}, [dispatch, pendingAction]);

	return {
		exploringDependencyId,
		isExploring: Boolean(exploringDependencyId),
		toggleExploration,
		pendingAction,
		dismissPendingAction,
		confirmPendingAction,
	};
}
