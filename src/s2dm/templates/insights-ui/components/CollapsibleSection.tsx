import { Button } from "@shared-ui/components/button";
import { cn } from "@shared-ui/utils/cn";
import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface CollapsibleSectionProps {
	title: string;
	defaultCollapsed?: boolean;
	children: React.ReactNode;
	className?: string;
	actions?: React.ReactNode;
	isCollapsed?: boolean;
	onCollapsedChange?: (isCollapsed: boolean) => void;
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
 * @param actions - Buttons that sit in the header, after the toggle button.
 * They do not toggle the body.
 * @param isCollapsed - Whether the body is closed. When set, the parent owns
 * the state and `defaultCollapsed` has no effect.
 * @param onCollapsedChange - Called with the new state when the user toggles
 * the body.
 * @returns The section.
 */
export function CollapsibleSection({
	title,
	defaultCollapsed = false,
	children,
	className,
	actions,
	isCollapsed: controlledIsCollapsed,
	onCollapsedChange,
}: CollapsibleSectionProps) {
	const [ownIsCollapsed, setOwnIsCollapsed] = useState(defaultCollapsed);
	let isCollapsed = ownIsCollapsed;
	if (controlledIsCollapsed !== undefined) {
		isCollapsed = controlledIsCollapsed;
	}

	let chevronIcon: React.ReactNode;
	if (isCollapsed) {
		chevronIcon = <ChevronDown className="h-4 w-4" />;
	} else {
		chevronIcon = <ChevronUp className="h-4 w-4" />;
	}

	const toggleCollapsed = () => {
		const nextIsCollapsed = !isCollapsed;
		setOwnIsCollapsed(nextIsCollapsed);
		onCollapsedChange?.(nextIsCollapsed);
	};
	const toggleClassName =
		"w-full flex items-center justify-between px-3 py-2 text-sm text-foreground border-0 bg-muted hover:bg-muted/80 transition-colors rounded h-auto";

	let header: React.ReactNode = (
		<Button
			type="button"
			variant="ghost"
			onClick={toggleCollapsed}
			className={toggleClassName}
		>
			<span>{title}</span>
			{chevronIcon}
		</Button>
	);
	if (actions) {
		let chevronLabel = "Collapse section";
		if (isCollapsed) {
			chevronLabel = "Expand section";
		}

		header = (
			<div className="flex items-center gap-1 rounded bg-muted py-1 pr-1">
				<Button
					type="button"
					variant="ghost"
					onClick={toggleCollapsed}
					aria-expanded={!isCollapsed}
					className={cn(toggleClassName, "min-w-0 flex-1 shrink")}
				>
					<span>{title}</span>
				</Button>
				{actions}
				<Button
					type="button"
					variant="ghost"
					size="icon-sm"
					onClick={toggleCollapsed}
					aria-expanded={!isCollapsed}
					aria-label={chevronLabel}
					title={chevronLabel}
				>
					{chevronIcon}
				</Button>
			</div>
		);
	}

	return (
		<div className={className}>
			{header}
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
