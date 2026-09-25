import {
	LedgerBadge,
	type LedgerBadgeTone,
} from "@/components/ledger/LedgerBadge";
import type { ModlStatus } from "@/ledger/modlProfile";

const STATUS_TONES: Record<ModlStatus, LedgerBadgeTone> = {
	ACTIVE: "active",
	SUPERSEDED: "superseded",
	REMOVED: "removed",
};

type StatusBadgeProps = {
	status: string;
	className?: string;
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
	return (
		<LedgerBadge
			tone={
				status in STATUS_TONES ? STATUS_TONES[status as ModlStatus] : "neutral"
			}
			className={className}
		>
			{status}
		</LedgerBadge>
	);
}
