import { ChevronRight } from "lucide-react";
import { Fragment } from "react";
import { cn } from "@shared-ui/utils/cn";

type BreadcrumbTone = "default" | "emphasis";

const BREADCRUMB_TONE_CLASSES: Record<BreadcrumbTone, string> = {
	default: "bg-sky-500/10",
	emphasis: "bg-sky-700/20",
};

const ELLIPSIS = "…";

type TypePathBreadcrumbProps = {
	segments: string[];
	tone?: BreadcrumbTone;
	maxSegments?: number;
	truncate?: boolean;
	scrollable?: boolean;
};

function collapseSegments(segments: string[], maxSegments: number): string[] {
	if (segments.length <= maxSegments) {
		return segments;
	}
	const head = segments.slice(0, maxSegments - 1);
	return [...head, ELLIPSIS, segments[segments.length - 1]];
}

export function TypePathBreadcrumb({
	segments,
	tone = "default",
	maxSegments,
	truncate = true,
	scrollable = false,
}: TypePathBreadcrumbProps) {
	const displaySegments = maxSegments
		? collapseSegments(segments, maxSegments)
		: segments;

	let containerClass: string;
	if (scrollable) {
		containerClass =
			"inline-flex items-center gap-1 whitespace-nowrap rounded-md px-2 py-1 text-sm text-card-foreground";
	} else if (truncate) {
		containerClass =
			"inline-block min-w-0 max-w-full truncate rounded-md px-2 py-1 text-sm text-card-foreground";
	} else {
		containerClass =
			"inline-flex max-w-full flex-wrap items-center gap-1 rounded-md px-2 py-1 text-sm text-card-foreground";
	}

	const inlineChevron = truncate && !scrollable;
	const chevronClass = inlineChevron
		? "mx-1 inline-block h-3.5 w-3.5 align-middle text-muted-foreground"
		: "h-3.5 w-3.5 shrink-0 text-muted-foreground";
	const segmentClass = scrollable
		? "shrink-0 whitespace-nowrap"
		: "min-w-0 break-words";

	return (
		<div
			title={inlineChevron ? segments.join(" › ") : undefined}
			className={cn(containerClass, BREADCRUMB_TONE_CLASSES[tone])}
		>
			{displaySegments.map((segment, index) => (
				<Fragment key={`${index}:${segment}`}>
					{index > 0 && <ChevronRight className={chevronClass} />}
					<span
						className={cn(
							segmentClass,
							segment === ELLIPSIS && "text-muted-foreground",
						)}
					>
						{segment}
					</span>
				</Fragment>
			))}
		</div>
	);
}
