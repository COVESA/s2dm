import { EvidenceRow } from "@insights-ui/components/EvidenceRow";
import { dimensionsOf, formatDimension } from "@ledger-ui/data/instances";
import { ABSENT_VALUE, formatValue } from "@ledger-ui/data/recordLabel";
import type { LedgerCell } from "@ledger-ui/data/types";

type RecordDetailsListProps = {
	cells: LedgerCell[];
};

type CellValueProps = {
	cell: LedgerCell;
};

/**
 * The value of one cell: one line per dimension for a value with the shape of
 * `instances` or `instance_tags`, the absent value when it holds no dimensions,
 * otherwise the formatted value.
 *
 * @param cell - The column and value to show.
 * @returns The lines of the dimensions, the absent value, or the formatted value.
 */
function CellValue({ cell }: CellValueProps) {
	const dimensions = dimensionsOf(cell.value);
	if (dimensions === null) {
		return <>{formatValue(cell.value)}</>;
	}
	if (dimensions.length === 0) {
		return <>{ABSENT_VALUE}</>;
	}
	return (
		<>
			{dimensions.map((dimension, index) => (
				// Tags of two entities can repeat a dimension name.
				<div key={`${index}:${dimension.name}`}>
					{formatDimension(dimension)}
				</div>
			))}
		</>
	);
}

export function RecordDetailsList({ cells }: RecordDetailsListProps) {
	return (
		<dl className="m-0 flex flex-col gap-2 p-0">
			{cells.map((cell, index) => (
				// A div per name-value group is what dl allows, and what EvidenceRow
				// renders, so the insights row styling applies without losing dl.
				<EvidenceRow
					key={`${index}:${cell.column}`}
					className="flex items-baseline justify-between gap-3 overflow-hidden"
				>
					<dt className="max-w-full shrink-0 truncate font-mono text-muted-foreground text-sm">
						{cell.column}
					</dt>
					{/* The sky tint insights uses for a type path, carried by the value
					    because that is what a reader scans for. */}
					<dd
						className="m-0 min-w-0 overflow-x-auto whitespace-nowrap rounded-md bg-sky-500/10 px-2 py-1 font-mono text-card-foreground text-sm"
						title={formatValue(cell.value)}
					>
						<CellValue cell={cell} />
					</dd>
				</EvidenceRow>
			))}
		</dl>
	);
}
