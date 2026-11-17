import { EmptyState } from "@shared-ui/components/empty-state";
import type { ReactNode } from "react";
import type { ReleasePage, ReleaseSummary } from "@/api/types";
import { ReleaseOption } from "@/components/releases/ReleaseOption";
import { ReleasePagination } from "@/components/releases/ReleasePagination";

type ReleaseListProps = {
	page: ReleasePage;
	isLoading: boolean;
	openingTag: string | null;
	selectedTag: string | null;
	onSelect: (release: ReleaseSummary) => void;
	onPageChange: (pageNumber: number) => void;
};

export function ReleaseList({
	page,
	isLoading,
	openingTag,
	selectedTag,
	onSelect,
	onPageChange,
}: ReleaseListProps) {
	const isLocked = openingTag !== null;

	let releaseList: ReactNode = (
		<ul className={"max-h-72 min-h-0 divide-y overflow-y-auto"}>
			{page.releases.map((release) => (
				<ReleaseOption
					key={release.tag}
					release={release}
					isSelected={release.tag === selectedTag}
					isOpening={release.tag === openingTag}
					isLocked={isLocked}
					onSelect={onSelect}
				/>
			))}
		</ul>
	);
	if (page.releases.length === 0) {
		releaseList = (
			<p className={"px-3 py-4 text-sm text-muted-foreground"}>
				No releases on this page.
			</p>
		);
	}
	if (isLoading) {
		releaseList = (
			<EmptyState
				isLoading={true}
				title={"Loading releases..."}
				className={"py-4"}
			/>
		);
	}

	return (
		<div className={"flex min-h-0 flex-col rounded-md border"}>
			{releaseList}
			<ReleasePagination
				page={page}
				isLoading={isLoading}
				onPageChange={onPageChange}
			/>
		</div>
	);
}
