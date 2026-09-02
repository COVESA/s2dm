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
import { useEffect, useMemo, useRef } from "react";
import { StatusBadge } from "@/components/ledger/StatusBadge";
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table";
import { toRecord } from "@/ledger/introspect";
import { STATUS_COLUMN } from "@/ledger/modlProfile";
import { formatValue } from "@/ledger/recordLabel";
import { isSameRow } from "@/ledger/resultRow";
import type { LedgerRecord, LedgerValue, QueryResult } from "@/ledger/types";
import type { LedgerCell } from "@/store/ledger/ledgerSlice";
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

type LedgerResultsGridProps = {
	result: QueryResult;
	selectedValues?: LedgerValue[] | null;
	containerClassName?: string;
	onRowClick?: (record: LedgerRecord, cells: LedgerCell[]) => void;
	sortable?: boolean;
};

function renderCell(columnName: string, value: LedgerValue): React.ReactNode {
	if (
		columnName === STATUS_COLUMN &&
		typeof value === "string" &&
		value.length > 0
	) {
		return <StatusBadge status={value} />;
	}
	return formatValue(value);
}

export function LedgerResultsGrid({
	result,
	selectedValues,
	containerClassName,
	onRowClick,
	sortable = true,
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

	// Queried by attribute because TableRow is a plain function component, which
	// cannot take a ref on React 18. The ref goes on the scroll container itself
	// rather than a wrapper, which would break the height max-h-full resolves against.
	const containerRef = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (!selectedValues || result.rows.length === 0) {
			return;
		}
		containerRef.current
			?.querySelector('[aria-selected="true"]')
			// "nearest" leaves an already-visible row where it is.
			?.scrollIntoView({ block: "nearest", inline: "nearest" });
	}, [selectedValues, result]);

	if (result.columns.length === 0) {
		return null;
	}

	return (
		<Table containerClassName={containerClassName} containerRef={containerRef}>
			<TableHeader>
				{table.getHeaderGroups().map((headerGroup) => (
					<TableRow key={headerGroup.id}>
						{headerGroup.headers.map((header) => {
							const sortDirection = header.column.getIsSorted();
							return (
								<TableHead key={header.id}>
									<button
										type="button"
										disabled={!sortable}
										onClick={
											sortable
												? header.column.getToggleSortingHandler()
												: undefined
										}
										className={cn(
											"flex items-center gap-1 font-mono text-xs",
											sortable && "cursor-pointer hover:text-foreground",
										)}
									>
										{header.column.columnDef.header as string}
										{sortable && sortDirection === "asc" && (
											<ArrowUp className="h-3 w-3" />
										)}
										{sortable && sortDirection === "desc" && (
											<ArrowDown className="h-3 w-3" />
										)}
										{sortable && !sortDirection && (
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
					const isSelected =
						selectedValues != null && isSameRow(row.original, selectedValues);
					return (
						<TableRow
							key={row.id}
							onClick={
								onRowClick
									? () =>
											onRowClick(
												record,
												result.columns.map((column, index) => ({
													column,
													value: row.original[index] ?? null,
												})),
											)
									: undefined
							}
							aria-selected={isSelected}
							className={cn(
								onRowClick && "cursor-pointer",
								isSelected && "bg-accent hover:bg-accent",
							)}
						>
							{row.getAllCells().map((cell, index) => (
								<TableCell key={cell.id} className="font-mono text-xs">
									{renderCell(
										result.columns[index] ?? "",
										cell.getValue() as LedgerValue,
									)}
								</TableCell>
							))}
						</TableRow>
					);
				})}
			</TableBody>
		</Table>
	);
}
