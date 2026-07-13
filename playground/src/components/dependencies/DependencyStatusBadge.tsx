import { RefreshCw } from "lucide-react";
import type { DependencyStatus } from "@/api/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/utils/cn";

type DependencyStatusBadgeProps = {
	status: DependencyStatus | null;
	isLoading: boolean;
	error: string | null;
	isRefreshDisabled: boolean;
	onRefresh: () => void;
};

type Presentation = {
	label: string;
	className: string;
};

function getPresentation(
	status: DependencyStatus | null,
	isLoading: boolean,
): Presentation {
	if (isLoading) {
		return {
			label: "Loading",
			className: "border-border bg-muted/70 text-muted-foreground",
		};
	}

	if (status === "resolved") {
		return {
			label: "Resolved",
			className:
				"border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
		};
	}

	if (status === "unresolved") {
		return {
			label: "Unresolved",
			className:
				"border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
		};
	}

	if (status === "invalid") {
		return {
			label: "Invalid",
			className:
				"border-destructive/30 bg-destructive/10 text-destructive dark:text-destructive",
		};
	}

	if (status === "not_configured") {
		return {
			label: "Not Configured",
			className: "border-border bg-muted/70 text-muted-foreground",
		};
	}

	return {
		label: "Unknown",
		className: "border-border bg-muted/70 text-muted-foreground",
	};
}

export function DependencyStatusBadge({
	status,
	isLoading,
	error,
	isRefreshDisabled,
	onRefresh,
}: DependencyStatusBadgeProps) {
	const presentation = getPresentation(status, isLoading);

	return (
		<>
			<span
				className={cn(
					"inline-flex h-8 items-center rounded-md border px-3 text-xs font-medium whitespace-nowrap",
					presentation.className,
				)}
				title={error || "Dependency resolution status"}
			>
				{presentation.label}
			</span>
			<Button
				variant="outline"
				size="icon-sm"
				onClick={onRefresh}
				loading={isLoading}
				disabled={isRefreshDisabled}
				title="Refresh dependency status"
			>
				{!isLoading && <RefreshCw className="h-4 w-4" />}
			</Button>
		</>
	);
}
