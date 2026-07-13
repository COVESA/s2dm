import { Package, PackageSearch, X } from "lucide-react";
import { FileListRow } from "@/components/FileListRow";
import { Button } from "@/components/ui/button";
import type { DependencyDraft } from "@/types/dependency";
import { cn } from "@/utils/cn";

type DependencyEntryProps = {
	dependency: DependencyDraft;
	isExploring: boolean;
	onToggleExplore: (dependency: DependencyDraft) => void;
};

export function DependencyEntry({
	dependency,
	isExploring,
	onToggleExplore,
}: DependencyEntryProps) {
	const label = `${dependency.name}@${dependency.version}`;
	const actionLabel = isExploring
		? `Stop exploring ${label}`
		: `Load dependency schema and selection for ${label}`;
	const actionIcon = isExploring ? <X /> : <PackageSearch />;

	return (
		<FileListRow
			title={label}
			label={label}
			icon={<Package className="h-4 w-4 flex-shrink-0" />}
			className={cn(isExploring && "border-primary/50 bg-accent/30")}
			trailing={
				<Button
					type="button"
					variant="ghost"
					size="icon-sm"
					onClick={() => onToggleExplore(dependency)}
					className={cn(
						"transition-opacity hover:bg-background/70",
						isExploring ? "opacity-100" : "opacity-0 group-hover:opacity-100",
					)}
					aria-label={actionLabel}
					title={actionLabel}
				>
					{actionIcon}
				</Button>
			}
		/>
	);
}
