import type { ReactNode } from "react";
import { Pane } from "@/components/Pane";
import { selectExploringDependencyId } from "@/store/deps/dependencyExploration/dependencyExplorationSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	selectResultPaneCollapsed,
	toggleResultPane,
} from "@/store/ui/uiSlice";

type DetailsPaneProps = {
	children: ReactNode;
	hasContent: boolean;
	position?: "none" | "left" | "center" | "right";
	collapsible?: boolean;
	className?: string;
};

export function DetailsPane({
	children,
	hasContent,
	position = "right",
	collapsible,
	className = "bg-card",
}: DetailsPaneProps) {
	const dispatch = useAppDispatch();
	const isCollapsed = useAppSelector(selectResultPaneCollapsed);
	const exploringDependencyId = useAppSelector(selectExploringDependencyId);
	const canCollapsePane = Boolean(
		collapsible && hasContent && !exploringDependencyId,
	);
	const shouldCollapsePane = !hasContent || isCollapsed;

	return (
		<Pane
			className={className}
			position={position}
			collapsible={canCollapsePane}
			isCollapsed={shouldCollapsePane}
			onToggleCollapse={
				canCollapsePane ? () => dispatch(toggleResultPane()) : undefined
			}
		>
			{children}
		</Pane>
	);
}
