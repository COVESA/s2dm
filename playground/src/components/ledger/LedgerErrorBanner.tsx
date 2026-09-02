import { StatusBanner } from "@/components/ui/status-banner";

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
			className={className ?? "whitespace-pre-wrap"}
		>
			{children}
		</StatusBanner>
	);
}
