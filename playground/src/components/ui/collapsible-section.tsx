import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface CollapsibleSectionProps {
	title: string;
	defaultCollapsed?: boolean;
	children: React.ReactNode;
	className?: string;
}

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
				className="w-full flex items-center justify-between px-3 py-2 text-sm text-foreground bg-muted hover:bg-muted/80 transition-colors rounded h-auto"
			>
				<span>{title}</span>
				{chevronIcon}
			</Button>
			<div
				className={cn(
					"px-2 overflow-hidden transition-all duration-300 ease-in-out",
					isCollapsed ? "max-h-0" : "max-h-100",
				)}
			>
				<div className="overflow-y-auto max-h-100">{children}</div>
			</div>
		</div>
	);
}
