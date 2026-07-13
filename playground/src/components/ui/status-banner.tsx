import { cn } from "@/utils/cn";

const VARIANT_CLASSES = {
	destructive: "border-destructive bg-destructive/10 text-destructive",
	warning:
		"border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
	success:
		"border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
} as const;

type StatusBannerVariant = keyof typeof VARIANT_CLASSES;

type StatusBannerProps = {
	variant: StatusBannerVariant;
	children: React.ReactNode;
	className?: string;
};

export function StatusBanner({
	variant,
	children,
	className,
}: StatusBannerProps) {
	return (
		<div
			className={cn(
				"rounded border p-2 text-sm",
				VARIANT_CLASSES[variant],
				className,
			)}
		>
			{children}
		</div>
	);
}
