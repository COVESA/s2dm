import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { LedgerResultsGrid } from "@/components/explore/ledger/LedgerResultsGrid";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { StatusBanner } from "@/components/ui/status-banner";
import { FILTERABLE_COLUMNS, LEDGER_PAGE_SIZE } from "@/ledger/constants";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	openLedgerDetail,
	selectIsLoadingLedgerRows,
	selectLedgerDetail,
	selectLedgerFilterOptions,
	selectLedgerFilters,
	selectLedgerPage,
	selectLedgerRows,
	selectLedgerRowsError,
	selectLedgerRowsTotal,
	selectLedgerSearch,
	selectLedgerTable,
	selectLedgerTables,
	selectSelectedLedgerTable,
	setLedgerFilter,
	setLedgerPage,
	setLedgerSearch,
} from "@/store/ledger/ledgerSlice";

// Radix Select treats "" as no selection, so the reset option needs a sentinel.
const ALL_VALUES = "__all__";

export function RawTablesView() {
	const dispatch = useAppDispatch();
	const tables = useAppSelector(selectLedgerTables);
	const selectedTable = useAppSelector(selectSelectedLedgerTable);
	const search = useAppSelector(selectLedgerSearch);
	const rows = useAppSelector(selectLedgerRows);
	const isLoadingRows = useAppSelector(selectIsLoadingLedgerRows);
	const rowsError = useAppSelector(selectLedgerRowsError);
	const total = useAppSelector(selectLedgerRowsTotal);
	const page = useAppSelector(selectLedgerPage);
	const detail = useAppSelector(selectLedgerDetail);
	const filters = useAppSelector(selectLedgerFilters);
	const filterOptions = useAppSelector(selectLedgerFilterOptions);

	const pageCount = Math.max(1, Math.ceil(total / LEDGER_PAGE_SIZE));
	const firstRow = total === 0 ? 0 : page * LEDGER_PAGE_SIZE + 1;
	const lastRow = Math.min(
		total,
		page * LEDGER_PAGE_SIZE + (rows?.rows.length ?? 0),
	);

	let content: React.ReactNode;
	if (rowsError) {
		content = (
			<StatusBanner variant="destructive" className="whitespace-pre-wrap">
				{rowsError}
			</StatusBanner>
		);
	} else if (!rows) {
		content = (
			<p className="text-sm text-muted-foreground">
				{isLoadingRows ? "Reading rows…" : "No rows loaded"}
			</p>
		);
	} else if (rows.rows.length === 0) {
		content = (
			<p className="text-sm text-muted-foreground">
				{search.trim() ? "No matching records" : "This table is empty"}
			</p>
		);
	} else {
		content = (
			<LedgerResultsGrid
				result={rows}
				containerClassName="max-h-full"
				selectedRecord={detail?.table === selectedTable ? detail.record : null}
				onRowClick={(record) =>
					dispatch(openLedgerDetail({ table: selectedTable, record }))
				}
			/>
		);
	}

	return (
		<div className="flex min-h-0 flex-1 flex-col">
			<div className="flex flex-col gap-3 border-b px-6 py-3">
				<div className="relative w-full">
					<Search className="absolute top-1/2 left-2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
					<Input
						value={search}
						onChange={(event) => dispatch(setLedgerSearch(event.target.value))}
						placeholder={`Search ${selectedTable}`}
						className="pl-8"
						aria-label={`Search ${selectedTable}`}
					/>
				</div>

				<div className="flex flex-wrap items-center gap-3">
					<Select
						value={selectedTable}
						onValueChange={(value) => dispatch(selectLedgerTable(value))}
					>
						<SelectTrigger className="w-48 shrink-0">
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							{tables.map((table) => (
								<SelectItem key={table.name} value={table.name}>
									<span className="capitalize">{table.name}</span>
									<span className="ml-2 font-mono text-muted-foreground text-xs">
										{table.rowCount}
									</span>
								</SelectItem>
							))}
						</SelectContent>
					</Select>

					{FILTERABLE_COLUMNS.map((column) => {
						const values = filterOptions[column];
						if (!values || values.length === 0) {
							return null;
						}
						return (
							<Select
								key={column}
								value={filters[column] ?? ALL_VALUES}
								onValueChange={(value) =>
									dispatch(
										setLedgerFilter({
											column,
											value: value === ALL_VALUES ? "" : value,
										}),
									)
								}
							>
								<SelectTrigger className="w-40 shrink-0">
									<SelectValue />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value={ALL_VALUES}>
										<span className="capitalize">All {column}</span>
									</SelectItem>
									{values.map((value) => (
										<SelectItem key={value} value={value}>
											{value}
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						);
					})}
				</div>
			</div>

			<div className="flex-1 overflow-auto px-6 py-4">{content}</div>

			{rows && total > 0 && (
				<div className="flex items-center justify-between gap-3 border-t px-6 py-3">
					<span className="text-sm text-muted-foreground tabular-nums">
						{firstRow}–{lastRow} of {total}
						{search.trim() ? " matching" : ""}
					</span>
					<div className="flex items-center gap-2">
						<span className="text-sm text-muted-foreground tabular-nums">
							Page {page + 1} of {pageCount}
						</span>
						<Button
							variant="outline"
							size="icon"
							onClick={() => dispatch(setLedgerPage(page - 1))}
							disabled={page === 0 || isLoadingRows}
							aria-label="Previous page"
							title="Previous page"
						>
							<ChevronLeft className="h-4 w-4" />
						</Button>
						<Button
							variant="outline"
							size="icon"
							onClick={() => dispatch(setLedgerPage(page + 1))}
							disabled={page + 1 >= pageCount || isLoadingRows}
							aria-label="Next page"
							title="Next page"
						>
							<ChevronRight className="h-4 w-4" />
						</Button>
					</div>
				</div>
			)}
		</div>
	);
}
