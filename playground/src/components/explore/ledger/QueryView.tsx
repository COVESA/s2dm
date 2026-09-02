import { LedgerResultsGrid } from "@/components/explore/ledger/LedgerResultsGrid";
import { QueryToolbar } from "@/components/explore/ledger/QueryToolbar";
import { LedgerErrorBanner } from "@/components/ledger/LedgerErrorBanner";
import { TextEditor } from "@/components/TextEditor";
import { StatusBanner } from "@/components/ui/status-banner";
import { matchResultTable } from "@/ledger/resultRecord";
import { recordValues } from "@/ledger/resultRow";
import type { LedgerValue } from "@/ledger/types";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	openLedgerDetail,
	selectLedgerDetail,
	selectLedgerQueryError,
	selectLedgerQueryResult,
	selectLedgerSql,
	selectLedgerTables,
	setLedgerSql,
} from "@/store/ledger/ledgerSlice";

export function QueryView() {
	const dispatch = useAppDispatch();
	const sql = useAppSelector(selectLedgerSql);
	const result = useAppSelector(selectLedgerQueryResult);
	const error = useAppSelector(selectLedgerQueryError);
	const tables = useAppSelector(selectLedgerTables);
	const detail = useAppSelector(selectLedgerDetail);

	// By column shape, not row count: whole records stay identifiable however
	// many of them the query returned.
	const recordTable = result ? matchResultTable(result.columns, tables) : null;

	// A projection carries its cells, which is the only faithful selection when
	// the query repeats a column name.
	let selectedValues: LedgerValue[] | null = null;
	if (result) {
		if (detail?.kind === "projection") {
			selectedValues =
				detail.cells.length === result.columns.length
					? detail.cells.map((cell) => cell.value)
					: null;
		} else if (recordTable && detail?.table === recordTable) {
			selectedValues = recordValues(detail.record, result.columns);
		}
	}

	let content: React.ReactNode;
	if (error) {
		content = <LedgerErrorBanner>{error}</LedgerErrorBanner>;
	} else if (!result) {
		content = (
			<p className="text-sm text-muted-foreground">
				Pick a predefined query or write your own, then run it
			</p>
		);
	} else if (result.rows.length === 0) {
		content = (
			<p className="text-sm text-muted-foreground">
				The query ran and returned no rows
			</p>
		);
	} else {
		content = (
			<LedgerResultsGrid
				result={result}
				containerClassName="max-h-full"
				selectedValues={selectedValues}
				onRowClick={(record, cells) =>
					dispatch(
						openLedgerDetail(
							recordTable
								? { kind: "row", table: recordTable, record }
								: { kind: "projection", record, cells },
						),
					)
				}
			/>
		);
	}

	return (
		<div className="flex min-h-0 flex-1 flex-col">
			<QueryToolbar />

			<div className="h-48 shrink-0 border-b">
				<TextEditor
					language="sql"
					value={sql}
					onChange={(value) => dispatch(setLedgerSql(value))}
					fullscreenTitle="Ledger query"
					fileName="query.sql"
				/>
			</div>

			<div className="flex-1 overflow-auto px-6 py-4">
				{result?.truncated && (
					<StatusBanner variant="warning" className="mb-3">
						Showing the first {result.rows.length} rows. Sorting applies to the
						loaded rows only.
					</StatusBanner>
				)}
				{content}
			</div>
		</div>
	);
}
