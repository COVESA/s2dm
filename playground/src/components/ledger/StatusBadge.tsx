import { cn } from "@/utils/cn";

const STATUS_CLASSES: Record<string, string> = {
	ACTIVE:
		"border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
	SUPERSEDED:
		"border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
	REMOVED: "border-destructive/40 bg-destructive/10 text-destructive",
};

type StatusBadgeProps = {
	status: string;
	className?: string;
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
	return (
		<span
			className={cn(
				"shrink-0 rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase",
				STATUS_CLASSES[status] ?? "border-border text-muted-foreground",
				className,
			)}
		>
			{status}
		</span>
	);
}
