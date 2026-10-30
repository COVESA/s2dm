import { cn } from "@shared-ui/utils/cn";
import { ArrowLeft, ArrowRight } from "lucide-react";

type InsightLinkButtonProps = {
	label: string;
	onClick?: () => void;
	/** "back" puts the arrow before the label and points it backwards. */
	direction?: "forward" | "back";
	className?: string;
};

export function InsightLinkButton({
	label,
	onClick,
	direction = "forward",
	className,
}: InsightLinkButtonProps) {
	const disabled = !onClick;
	const pointsBack = direction === "back";

	let arrowIcon = <ArrowRight className="h-4 w-4" />;
	if (pointsBack) {
		arrowIcon = <ArrowLeft className="h-4 w-4" />;
	}

	return (
		<button
			type="button"
			disabled={disabled}
			onClick={onClick}
			className={cn(
				// border-0 and bg-transparent defeat Infima's button styling on the
				// documentation website; Tailwind Preflight already implies both.
				"inline-flex items-center gap-1 self-start border-0 bg-transparent text-sm font-medium",
				disabled
					? "cursor-not-allowed text-muted-foreground"
					: "cursor-pointer text-primary hover:underline",
				className,
			)}
		>
			{pointsBack && arrowIcon}
			{label}
			{!pointsBack && arrowIcon}
		</button>
	);
}
