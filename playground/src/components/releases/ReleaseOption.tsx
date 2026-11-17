import { cn } from "@shared-ui/utils/cn";
import { Loader2 } from "lucide-react";
import type { ReleaseSummary } from "@/api/types";

const UNSUPPORTED_RELEASE_TITLE = "This release has no supported schema asset.";
const PUBLISH_DATE_FORMAT: Intl.DateTimeFormatOptions = {
	year: "numeric",
	month: "2-digit",
	day: "2-digit",
};

type ReleaseOptionProps = {
	release: ReleaseSummary;
	isSelected: boolean;
	isOpening: boolean;
	isLocked: boolean;
	onSelect: (release: ReleaseSummary) => void;
};

export function ReleaseOption({
	release,
	isSelected,
	isOpening,
	isLocked,
	onSelect,
}: ReleaseOptionProps) {
	const isSupported = release.candidate_assets.length > 0;

	let optionTitle: string | undefined;
	if (!isSupported) {
		optionTitle = UNSUPPORTED_RELEASE_TITLE;
	}

	let releaseName: string | null = null;
	if (release.name && release.name !== release.tag) {
		releaseName = release.name;
	}

	let publishDate: string | null = null;
	if (release.published_at) {
		const publishTime = new Date(release.published_at);
		publishDate = publishTime.toLocaleDateString(
			undefined,
			PUBLISH_DATE_FORMAT,
		);
	}

	return (
		<li title={optionTitle}>
			<button
				type={"button"}
				disabled={!isSupported || isLocked}
				onClick={() => onSelect(release)}
				className={cn(
					"flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-left text-sm hover:bg-accent disabled:cursor-not-allowed disabled:hover:bg-transparent",
					!isSupported && "opacity-50",
					isSelected && "bg-accent",
				)}
			>
				<span className={"font-medium"}>{release.tag}</span>
				{releaseName !== null && (
					<span className={"truncate text-muted-foreground"}>
						{releaseName}
					</span>
				)}
				<span
					className={
						"ml-auto flex shrink-0 items-center gap-2 text-xs text-muted-foreground"
					}
				>
					{release.prerelease && (
						<span className={"rounded border px-1"}>Pre-release</span>
					)}
					{publishDate !== null && <span>{publishDate}</span>}
					{isOpening && <Loader2 className={"h-4 w-4 animate-spin"} />}
				</span>
			</button>
		</li>
	);
}
