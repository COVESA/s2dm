import { CollapsibleSection } from "@insights-ui/components/CollapsibleSection";
import { Button } from "@shared-ui/components/button";
import { StatusBanner } from "@shared-ui/components/status-banner";
import { X } from "lucide-react";
import type { ReactNode } from "react";
import type { ReleaseSummary } from "@/api/types";
import { ReleaseArchiveDialog } from "@/components/releases/ReleaseArchiveDialog";
import { ReleaseList } from "@/components/releases/ReleaseList";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	dismissArchiveChoices,
	exploreRelease,
	fetchReleasePage,
	openRelease,
	selectReleases,
} from "@/store/releases/releasesSlice";
import { getLoadedReleaseId, getRepositoryPath } from "@/types/release";

type ReleasesSectionProps = {
	exploringReleaseId: string | null;
	onStopExploring: () => void;
};

export function ReleasesSection({
	exploringReleaseId,
	onStopExploring,
}: ReleasesSectionProps) {
	const dispatch = useAppDispatch();
	const releases = useAppSelector(selectReleases);

	const page = releases.page;
	const isExploringRelease = exploringReleaseId !== null;
	const hasPageError = releases.pageError !== null;
	if (page === null && !isExploringRelease && !hasPageError) {
		return null;
	}

	const selectedRelease = releases.selectedRelease;
	const isOpening = releases.openingTag !== null;
	const isChoosingArchive = releases.archiveChoices !== null;

	let openError: string | null = null;
	if (!isChoosingArchive) {
		openError = releases.openError;
	}
	const hasFooter = hasPageError || openError !== null;

	const exploredRelease = releases.loadedReleases.find(
		(loadedRelease) => loadedRelease.id === exploringReleaseId,
	);
	let exploredTag: string | null = null;
	if (exploredRelease) {
		const pageReleaseId = getLoadedReleaseId(
			releases.repository,
			exploredRelease.tag,
		);
		if (pageReleaseId === exploredRelease.id) {
			exploredTag = exploredRelease.tag;
		}
	}

	const handleSelectRelease = (release: ReleaseSummary) => {
		const exploreAction = exploreRelease(release);
		dispatch(exploreAction);
	};

	const handlePageChange = (pageNumber: number) => {
		const fetchAction = fetchReleasePage({
			repository: releases.repository,
			page: pageNumber,
		});
		dispatch(fetchAction);
	};

	const handlePickArchive = (archiveName: string) => {
		if (!selectedRelease) {
			return;
		}
		const openAction = openRelease({
			release: selectedRelease,
			artifact: archiveName,
		});
		dispatch(openAction);
	};

	const handleCancelArchive = () => {
		const dismissAction = dismissArchiveChoices();
		dispatch(dismissAction);
	};

	let releaseList: ReactNode = null;
	if (page !== null) {
		releaseList = (
			<div className={"flex min-h-0 flex-col py-2"}>
				<ReleaseList
					page={page}
					isLoading={releases.isLoadingPage}
					openingTag={releases.openingTag}
					selectedTag={exploredTag}
					onSelect={handleSelectRelease}
					onPageChange={handlePageChange}
				/>
			</div>
		);
	}

	const repositoryPath = getRepositoryPath(releases.repository);
	const sectionTitle = `${repositoryPath} releases`;
	const sectionActions = (
		<div className={"flex items-center"}>
			{isExploringRelease && (
				<Button
					type={"button"}
					variant={"outline"}
					size={"icon-sm"}
					onClick={onStopExploring}
					aria-label={"Stop exploring releases"}
					title={"Stop exploring releases"}
				>
					<X />
				</Button>
			)}
		</div>
	);

	return (
		<div className={"flex min-h-0 flex-col space-y-2 pb-2"}>
			<CollapsibleSection title={sectionTitle} actions={sectionActions}>
				{releaseList}
			</CollapsibleSection>
			{hasFooter && (
				<div className={"space-y-2 px-2"}>
					{hasPageError && (
						<StatusBanner variant={"destructive"}>
							{releases.pageError}
						</StatusBanner>
					)}
					{openError !== null && (
						<StatusBanner variant={"destructive"}>{openError}</StatusBanner>
					)}
				</div>
			)}
			<ReleaseArchiveDialog
				choices={releases.archiveChoices}
				isOpening={isOpening}
				error={releases.openError}
				onPick={handlePickArchive}
				onCancel={handleCancelArchive}
			/>
		</div>
	);
}
