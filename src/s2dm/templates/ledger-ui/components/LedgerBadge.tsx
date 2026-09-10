import { cn } from "@/utils/cn";

export type LedgerBadgeTone = "active" | "superseded" | "removed" | "neutral";

const TONE_CLASSES: Record<LedgerBadgeTone, string> = {
	active:
		"border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
	superseded:
		"border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
	removed: "border-destructive/40 bg-destructive/10 text-destructive",
	neutral: "border-border bg-muted/70 text-muted-foreground",
};

type LedgerBadgeProps = {
	tone?: LedgerBadgeTone;
	children: React.ReactNode;
	className?: string;
	title?: string;
};

export function LedgerBadge({
	tone = "neutral",
	children,
	className,
	title,
}: LedgerBadgeProps) {
	return (
		<span
			title={title}
			className={cn(
				"inline-flex shrink-0 items-center rounded-md border px-2 py-0.5 font-medium text-xs whitespace-nowrap",
				TONE_CLASSES[tone],
				className,
			)}
		>
			{children}
		</span>
	);
}
