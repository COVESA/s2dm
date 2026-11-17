import { EmptyState } from "@shared-ui/components/empty-state";
import { useEffect } from "react";
import { ReleaseRepositoryForm } from "@/components/releases/ReleaseRepositoryForm";
import { ReleasesSection } from "@/components/releases/ReleasesSection";
import { SchemaEditor } from "@/components/SchemaEditor";
import { Separator } from "@/components/ui/separator";
import { useExploration } from "@/hooks/useExploration";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	clearOpenedRelease,
	selectOpenedRelease,
	selectReleases,
} from "@/store/releases/releasesSlice";

export function ReleasesWorkspace() {
	const dispatch = useAppDispatch();
	const releases = useAppSelector(selectReleases);
	const openedRelease = useAppSelector(selectOpenedRelease);
	const { exploringReleaseId, exploreTarget, stopExploration } =
		useExploration();

	useEffect(() => {
		if (openedRelease === null) {
			return;
		}
		exploreTarget({ kind: "release", release: openedRelease });
		const clearAction = clearOpenedRelease();
		dispatch(clearAction);
	}, [dispatch, exploreTarget, openedRelease]);

	const isExploringRelease = exploringReleaseId !== null;
	const isRepositoryLoaded = releases.page !== null;
	const isEmpty = !isRepositoryLoaded && !isExploringRelease;

	return (
		<div className={"flex min-h-0 flex-1 flex-col"}>
			<ReleaseRepositoryForm />

			<ReleasesSection
				exploringReleaseId={exploringReleaseId}
				onStopExploring={stopExploration}
			/>

			{isExploringRelease && (
				<>
					<Separator />
					<SchemaEditor emptyMessage={"Nothing to display"} />
				</>
			)}

			{isEmpty && <EmptyState title={"Nothing to display"} />}
		</div>
	);
}
