import type { ReactNode } from "react";
import { cn } from "@shared-ui/utils/cn";

type EvidenceRowProps = {
	children: ReactNode;
	/** Set to false when an inner element owns the padding, e.g. a full-row button. */
	padded?: boolean;
	className?: string;
};

export function EvidenceRow({
	children,
	padded = true,
	className,
}: EvidenceRowProps) {
	return (
		<div
			className={cn(
				"rounded-md border border-border",
				padded && "px-3 py-2",
				className,
			)}
		>
			{children}
		</div>
	);
}
