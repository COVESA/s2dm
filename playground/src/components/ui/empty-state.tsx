import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type EmptyStateProps = {
	title?: string;
	isLoading?: boolean;
	children?: React.ReactNode;
	className?: string;
};

export function EmptyState({
	title,
	isLoading = false,
	children,
	className,
}: EmptyStateProps) {
	if (children) {
		return (
			<div
				className={cn(
					"flex-1 flex flex-col gap-4 text-muted-foreground",
					className,
				)}
			>
				{children}
			</div>
		);
	}

	const displayTitle = title ?? "Nothing to show";

	return (
		<div
			className={cn(
				"flex-1 flex flex-col items-center justify-center gap-4 text-muted-foreground",
				className,
			)}
		>
			{isLoading && <Loader2 className="w-6 h-6 animate-spin" />}
			<p>{displayTitle}</p>
		</div>
	);
}
