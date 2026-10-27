import { cn } from "@shared-ui/utils/cn";
import type { ReactNode } from "react";

type HighlightableCardProps = {
	children: ReactNode;
	selected?: boolean;
	className?: string;
};

export function HighlightableCard({
	children,
	selected,
	className,
}: HighlightableCardProps) {
	return (
		<div
			className={cn(
				"flex flex-col gap-4 rounded-lg border bg-card p-5 transition-colors",
				selected ? "border-primary ring-1 ring-primary" : "border-border",
				className,
			)}
		>
			{children}
		</div>
	);
}
