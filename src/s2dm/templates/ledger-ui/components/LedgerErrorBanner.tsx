import { StatusBanner } from "@shared-ui/components/status-banner";
import { cn } from "@shared-ui/utils/cn";

type LedgerErrorBannerProps = {
	children: React.ReactNode;
	className?: string;
};

export function LedgerErrorBanner({
	children,
	className,
}: LedgerErrorBannerProps) {
	return (
		<StatusBanner
			variant="destructive"
			className={cn("whitespace-pre-wrap", className)}
		>
			{children}
		</StatusBanner>
	);
}
