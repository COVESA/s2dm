import { CollapsibleSection } from "@insights-ui/components/CollapsibleSection";
import { Button } from "@shared-ui/components/button";
import { StatusBanner } from "@shared-ui/components/status-banner";
import { Hammer } from "lucide-react";
import { useCallback, useMemo } from "react";
import { DependencyEntry } from "@/components/DependencyEntry";
import { BuildOptionsPopover } from "@/components/dependencies/BuildOptionsPopover";
import { BuiltSchemaViewerButton } from "@/components/dependencies/BuiltSchemaViewerButton";
import { useExploration } from "@/hooks/useExploration";
import {
	composeDependencies,
	selectComposeError,
	selectComposeMessage,
	selectIsComposing,
} from "@/store/deps/compose/composeSlice";
import {
	selectDependencyDrafts,
	selectIsLoadingDependencyStatus,
	selectIsSavingDependenciesConfig,
} from "@/store/deps/depsSlice";
import { selectIsSavingIdentities } from "@/store/deps/identities/identitiesSlice";
import { selectIsResolvingDependencies } from "@/store/deps/resolve/resolveSlice";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { type DependencyDraft, hasSchemaContent } from "@/types/dependency";

type ResolvedDependenciesSectionProps = {
	isCollapsed: boolean;
	onCollapsedChange: (isCollapsed: boolean) => void;
};

export function ResolvedDependenciesSection({
	isCollapsed,
	onCollapsedChange,
}: ResolvedDependenciesSectionProps) {
	const dispatch = useAppDispatch();
	const dependencies = useAppSelector(selectDependencyDrafts);
	const isComposing = useAppSelector(selectIsComposing);
	const composeError = useAppSelector(selectComposeError);
	const composeMessage = useAppSelector(selectComposeMessage);
	const isDependencyStatusLoading = useAppSelector(
		selectIsLoadingDependencyStatus,
	);
	const isDependenciesSaving = useAppSelector(selectIsSavingDependenciesConfig);
	const isDependenciesResolving = useAppSelector(selectIsResolvingDependencies);
	const isIdentitiesSaving = useAppSelector(selectIsSavingIdentities);

	const resolvedDependencies = useMemo(
		() => dependencies.filter(hasSchemaContent),
		[dependencies],
	);

	const { exploringDependencyId, toggleExploration } = useExploration();

	const handleToggleExplore = (dependency: DependencyDraft) => {
		toggleExploration({ kind: "dependency", dependency });
	};

	const handleCompose = useCallback(() => {
		dispatch(composeDependencies());
	}, [dispatch]);

	const isComposeDisabled =
		isDependencyStatusLoading ||
		isDependenciesSaving ||
		isIdentitiesSaving ||
		isDependenciesResolving ||
		isComposing;

	const dependencyCountText = `${resolvedDependencies.length} dependenc${resolvedDependencies.length === 1 ? "y" : "ies"}`;
	const hasComposeStatus = Boolean(composeError || composeMessage);

	const buildActions = (
		<div className={"flex items-center gap-1"}>
			<BuiltSchemaViewerButton size={"icon-sm"} />
			<div className={"flex items-center"}>
				<Button
					variant={"outline"}
					size={"icon-sm"}
					onClick={handleCompose}
					loading={isComposing}
					disabled={isComposeDisabled}
					title={"Build dependencies"}
					className={"rounded-r-none"}
				>
					{!isComposing && <Hammer />}
				</Button>
				<BuildOptionsPopover disabled={isComposeDisabled} />
			</div>
		</div>
	);

	return (
		<div className="flex min-h-0 flex-col space-y-2">
			<CollapsibleSection
				title={dependencyCountText}
				actions={buildActions}
				isCollapsed={isCollapsed}
				onCollapsedChange={onCollapsedChange}
			>
				<ul className="min-h-0 space-y-1 overflow-y-auto py-2">
					{resolvedDependencies.map((dependency) => (
						<DependencyEntry
							key={dependency.id}
							dependency={dependency}
							isExploring={dependency.id === exploringDependencyId}
							onToggleExplore={handleToggleExplore}
						/>
					))}
				</ul>
			</CollapsibleSection>
			{hasComposeStatus && (
				<div className="px-2 space-y-2">
					{composeError && (
						<StatusBanner variant="destructive">{composeError}</StatusBanner>
					)}
					{composeMessage && (
						<StatusBanner variant="success">{composeMessage}</StatusBanner>
					)}
				</div>
			)}
		</div>
	);
}
