import {
	createSortedRowModel,
	rowSortingFeature,
	sortFn_alphanumeric,
	sortFn_basic,
	sortFn_text,
	tableFeatures,
	useTable,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import { useMemo } from "react";
import { StatusBadge } from "@/components/ledger/StatusBadge";
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table";
import type { LedgerRecord, LedgerValue, QueryResult } from "@/ledger/types";
import { cn } from "@/utils/cn";

const features = tableFeatures({
	rowSortingFeature,
	sortedRowModel: createSortedRowModel(),
	sortFns: {
		alphanumeric: sortFn_alphanumeric,
		basic: sortFn_basic,
		text: sortFn_text,
	},
});

export type LedgerRow = Record<string, LedgerValue>;

type LedgerResultsGridProps = {
	result: QueryResult;
	selectedRecord?: LedgerRecord | null;
	containerClassName?: string;
	onRowClick?: (row: LedgerRow) => void;
};

function toRecord(row: LedgerValue[], columns: string[]): LedgerRecord {
	return Object.fromEntries(
		columns.map((column, index) => [column, row[index] ?? null]),
	);
}

// By value, not identity: rows from the chain view are re-read from the database.
function isSameRecord(
	left: LedgerRecord,
	right: LedgerRecord,
	columns: string[],
): boolean {
	return columns.every((column) => {
		const a = left[column] ?? null;
		const b = right[column] ?? null;
		return a instanceof Uint8Array || b instanceof Uint8Array ? false : a === b;
	});
}

function renderCell(columnId: string, value: LedgerValue): React.ReactNode {
	if (columnId === "status" && typeof value === "string" && value.length > 0) {
		return <StatusBadge status={value} />;
	}
	return formatValue(value);
}

function formatValue(value: LedgerValue): string {
	if (value === null) {
		return "—";
	}
	if (value instanceof Uint8Array) {
		return `${value.byteLength} bytes`;
	}
	return String(value);
}

export function LedgerResultsGrid({
	result,
	selectedRecord,
	containerClassName,
	onRowClick,
}: LedgerResultsGridProps) {
	// By position: a repeated column name would collapse in a keyed record.
	const data = useMemo<LedgerValue[][]>(() => result.rows, [result.rows]);

	const columns = useMemo(
		() =>
			result.columns.map((column, index) => ({
				id: `${index}:${column}`,
				header: column,
				accessorFn: (row: LedgerValue[]) => row[index] ?? null,
			})),
		[result.columns],
	);

	const table = useTable({ features, columns, data });

	if (result.columns.length === 0) {
		return null;
	}

	return (
		<Table containerClassName={containerClassName}>
			<TableHeader>
				{table.getHeaderGroups().map((headerGroup) => (
					<TableRow key={headerGroup.id}>
						{headerGroup.headers.map((header) => {
							const sortDirection = header.column.getIsSorted();
							return (
								<TableHead key={header.id}>
									<button
										type="button"
										onClick={header.column.getToggleSortingHandler()}
										className="flex cursor-pointer items-center gap-1 font-mono text-xs hover:text-foreground"
									>
										{header.column.columnDef.header as string}
										{sortDirection === "asc" && <ArrowUp className="h-3 w-3" />}
										{sortDirection === "desc" && (
											<ArrowDown className="h-3 w-3" />
										)}
										{!sortDirection && (
											<ChevronsUpDown className="h-3 w-3 opacity-40" />
										)}
									</button>
								</TableHead>
							);
						})}
					</TableRow>
				))}
			</TableHeader>
			<TableBody>
				{table.getRowModel().rows.map((row) => {
					const record = toRecord(row.original, result.columns);
					const isSelected = selectedRecord
						? isSameRecord(record, selectedRecord, result.columns)
						: false;
					return (
						<TableRow
							key={row.id}
							onClick={onRowClick ? () => onRowClick(record) : undefined}
							aria-selected={isSelected}
							className={cn(
								onRowClick && "cursor-pointer",
								isSelected && "bg-accent hover:bg-accent",
							)}
						>
							{row.getAllCells().map((cell) => (
								<TableCell key={cell.id} className="font-mono text-xs">
									{renderCell(cell.column.id, cell.getValue() as LedgerValue)}
								</TableCell>
							))}
						</TableRow>
					);
				})}
			</TableBody>
		</Table>
	);
}
