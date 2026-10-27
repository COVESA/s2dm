import type { ReactNode } from "react";
import { cn } from "@shared-ui/utils/cn";

type CardSummaryProps = {
	children: ReactNode;
	className?: string;
};

/**
 * The stack of subtitle lines that sits under a card's title.
 *
 * @param children - The `CardSubtitle` lines to stack.
 * @param className - Extra classes, merged last so callers can override the spacing.
 * @returns The wrapper element.
 */
export function CardSummary({ children, className }: CardSummaryProps) {
	return (
		<div className={cn("mb-4 flex flex-col gap-1", className)}>{children}</div>
	);
}

type CardSubtitleProps = {
	children: ReactNode;
	/** Renders the muted follow-up line instead of the headline. */
	muted?: boolean;
	className?: string;
};

/**
 * One subtitle line of a card.
 *
 * Carries its own margin reset so the package never depends on the host loading
 * Tailwind's Preflight. The Docusaurus site deliberately omits Preflight to leave
 * Infima's document styling intact, which would otherwise stack a paragraph margin
 * on top of the gap between the lines.
 *
 * @param children - The line's content.
 * @param muted - Renders the muted follow-up line instead of the headline.
 * @param className - Extra classes, merged last so callers can override the colour.
 * @returns The paragraph element.
 */
export function CardSubtitle({
	children,
	muted,
	className,
}: CardSubtitleProps) {
	let toneClassName = "text-card-foreground";
	if (muted) {
		toneClassName = "text-muted-foreground";
	}

	return (
		<p className={cn("m-0 text-sm", toneClassName, className)}>{children}</p>
	);
}
