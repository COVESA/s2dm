import {
	LedgerBadge,
	type LedgerBadgeTone,
} from "@/components/ledger/LedgerBadge";

const STATUS_TONES: Record<string, LedgerBadgeTone> = {
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
		<LedgerBadge tone={STATUS_TONES[status] ?? "neutral"} className={className}>
			{status}
		</LedgerBadge>
	);
}
