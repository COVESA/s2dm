import { cn } from "@shared-ui/utils/cn";
import type { ReactNode } from "react";

type EvidenceListProps = {
	children: ReactNode;
	className?: string;
};

/**
 * A vertical list of evidence rows.
 *
 * Carries its own list reset so the package never depends on the host loading
 * Tailwind's Preflight. The Docusaurus site deliberately omits Preflight to leave
 * Infima's document styling intact, which would otherwise give evidence rows a
 * marker and an indent.
 *
 * @param children - The `<li>` rows to render.
 * @param className - Extra classes, merged last so callers can override the spacing.
 * @returns The list element.
 */
export function EvidenceList({ children, className }: EvidenceListProps) {
	return (
		<ul className={cn("m-0 flex list-none flex-col gap-2 p-0", className)}>
			{children}
		</ul>
	);
}
