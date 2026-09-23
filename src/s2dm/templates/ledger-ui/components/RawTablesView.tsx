import { LedgerErrorBanner } from "@ledger-ui/components/LedgerErrorBanner";
import { LedgerFilterSelects } from "@ledger-ui/components/LedgerFilterSelects";
import { LedgerResultsGrid } from "@ledger-ui/components/LedgerResultsGrid";
import { LedgerSearchInput } from "@ledger-ui/components/LedgerSearchInput";
import { LedgerTableFooter } from "@ledger-ui/components/LedgerTableFooter";
import { capitalise } from "@ledger-ui/data/recordLabel";
import { recordValues } from "@ledger-ui/data/resultRow";
import { useLedgerDispatch, useLedgerSelector } from "@ledger-ui/state/hooks";
import {
	chooseLedgerTable,
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
	selectLedgerTables,
	selectSelectedLedgerTable,
	setLedgerSearch,
} from "@ledger-ui/state/ledgerSlice";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";

export function RawTablesView() {
	const dispatch = useLedgerDispatch();
	const tables = useLedgerSelector(selectLedgerTables);
	const selectedTable = useLedgerSelector(selectSelectedLedgerTable);
	const search = useLedgerSelector(selectLedgerSearch);
	const rows = useLedgerSelector(selectLedgerRows);
	const isLoadingRows = useLedgerSelector(selectIsLoadingLedgerRows);
	const rowsError = useLedgerSelector(selectLedgerRowsError);
	const total = useLedgerSelector(selectLedgerRowsTotal);
	const page = useLedgerSelector(selectLedgerPage);
	const detail = useLedgerSelector(selectLedgerDetail);
	const filters = useLedgerSelector(selectLedgerFilters);
	const filterOptions = useLedgerSelector(selectLedgerFilterOptions);

	const selectedValues =
		rows && detail?.kind === "row" && detail.table === selectedTable
			? recordValues(detail.record, rows.columns)
			: null;
	const matchingLabel = search.trim() ? " matching" : "";

	let content: React.ReactNode;
	if (rowsError) {
		content = <LedgerErrorBanner>{rowsError}</LedgerErrorBanner>;
	} else if (!rows) {
		const message = isLoadingRows ? "Reading rows…" : "No rows loaded";
		content = <p className="text-sm text-muted-foreground">{message}</p>;
	} else if (rows.rows.length === 0) {
		const message = search.trim()
			? "No matching records"
			: "This table is empty";
		content = <p className="text-sm text-muted-foreground">{message}</p>;
	} else {
		content = (
			<LedgerResultsGrid
				result={rows}
				containerClassName="max-h-full"
				selectedValues={selectedValues}
				onRowClick={(record) =>
					dispatch(
						openLedgerDetail({ kind: "row", table: selectedTable, record }),
					)
				}
			/>
		);
	}

	return (
		<div className="flex min-h-0 flex-1 flex-col">
			<div className="flex flex-col gap-3 border-b px-6 py-3">
				<LedgerSearchInput
					value={search}
					onChange={(value) => dispatch(setLedgerSearch(value))}
					label={`Search ${selectedTable}`}
				/>

				<div className="flex flex-wrap items-center gap-3">
					<Select
						value={selectedTable}
						onValueChange={(value) => dispatch(chooseLedgerTable(value))}
					>
						<SelectTrigger className="w-48 shrink-0">
							<SelectValue />
						</SelectTrigger>
						<SelectContent>
							{tables.map((table) => (
								<SelectItem key={table.name} value={table.name}>
									<span>{capitalise(table.name)}</span>
									<span className="ml-2 font-mono text-muted-foreground text-xs">
										{table.rowCount}
									</span>
								</SelectItem>
							))}
						</SelectContent>
					</Select>

					<LedgerFilterSelects
						filters={filters}
						filterOptions={filterOptions}
					/>
				</div>
			</div>

			<div className="flex-1 overflow-auto px-6 py-4">{content}</div>

			{rows && total > 0 && (
				<LedgerTableFooter
					total={total}
					page={page}
					isLoadingRows={isLoadingRows}
					matchingLabel={matchingLabel}
				/>
			)}
		</div>
	);
}
