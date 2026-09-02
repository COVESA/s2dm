import { EvidenceRow } from "@insights-ui/components/EvidenceRow";
import { formatValue } from "@/ledger/recordLabel";
import type { LedgerCell } from "@/store/ledger/ledgerSlice";

type RecordDetailsListProps = {
	cells: LedgerCell[];
};

export function RecordDetailsList({ cells }: RecordDetailsListProps) {
	return (
		<dl className="m-0 flex flex-col gap-2 p-0">
			{cells.map((cell, index) => (
				// A div per name-value group is what dl allows, and what EvidenceRow
				// renders, so the insights row styling applies without losing dl.
				<EvidenceRow
					key={`${index}:${cell.column}`}
					className="flex items-baseline justify-between gap-3"
				>
					<dt className="shrink-0 font-mono text-muted-foreground text-xs">
						{cell.column}
					</dt>
					{/* The sky tint insights uses for a type path, carried by the value
					    because that is what a reader scans for. */}
					<dd
						className="m-0 min-w-0 truncate rounded-md bg-sky-500/10 px-2 py-1 font-mono text-card-foreground text-xs"
						title={formatValue(cell.value)}
					>
						{formatValue(cell.value)}
					</dd>
				</EvidenceRow>
			))}
		</dl>
	);
}
