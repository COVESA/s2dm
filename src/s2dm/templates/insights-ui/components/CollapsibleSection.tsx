import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { Button } from "@shared-ui/components/button";
import { cn } from "@shared-ui/utils/cn";

interface CollapsibleSectionProps {
	title: string;
	defaultCollapsed?: boolean;
	children: React.ReactNode;
	className?: string;
}

/**
 * A titled section whose body collapses behind its header.
 *
 * The body animates between `0fr` and `1fr` grid rows rather than a max-height, so
 * it expands to whatever the content actually needs instead of scrolling past a cap.
 * The header carries `border-0` because Docusaurus gives a raw button a border that
 * Tailwind's Preflight would otherwise have removed; it is inert where Preflight runs.
 *
 * @param title - Header text, and the click target that toggles the body.
 * @param defaultCollapsed - Whether the body starts closed.
 * @param children - The body content.
 * @param className - Extra classes for the outer element.
 * @returns The section.
 */
export function CollapsibleSection({
	title,
	defaultCollapsed = false,
	children,
	className,
}: CollapsibleSectionProps) {
	const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);

	let chevronIcon: React.ReactNode;
	if (isCollapsed) {
		chevronIcon = <ChevronDown className="h-4 w-4" />;
	} else {
		chevronIcon = <ChevronUp className="h-4 w-4" />;
	}

	return (
		<div className={className}>
			<Button
				type="button"
				variant="ghost"
				onClick={() => setIsCollapsed(!isCollapsed)}
				className="w-full flex items-center justify-between px-3 py-2 text-sm text-foreground border-0 bg-muted hover:bg-muted/80 transition-colors rounded h-auto"
			>
				<span>{title}</span>
				{chevronIcon}
			</Button>
			<div
				className={cn(
					"px-2 grid transition-all duration-300 ease-in-out",
					isCollapsed ? "grid-rows-[0fr]" : "grid-rows-[1fr]",
				)}
			>
				<div className="overflow-hidden">{children}</div>
			</div>
		</div>
	);
}
