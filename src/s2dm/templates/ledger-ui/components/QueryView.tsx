import { LedgerErrorBanner } from "@ledger-ui/components/LedgerErrorBanner";
import { LedgerResultsGrid } from "@ledger-ui/components/LedgerResultsGrid";
import { QueryToolbar } from "@ledger-ui/components/QueryToolbar";
import { matchResultTable } from "@ledger-ui/data/resultRecord";
import { recordValues } from "@ledger-ui/data/resultRow";
import type { LedgerValue } from "@ledger-ui/data/types";
import { useLedgerDispatch, useLedgerSelector } from "@ledger-ui/state/hooks";
import {
	openLedgerQueryRow,
	selectLedgerDetail,
	selectLedgerQueryError,
	selectLedgerQueryResult,
	selectLedgerSql,
	selectLedgerTables,
	setLedgerSql,
} from "@ledger-ui/state/ledgerSlice";
import { TextEditor } from "@/components/TextEditor";
import { StatusBanner } from "@/components/ui/status-banner";

// Its own component so that typing re-renders the editor alone: the view below
// lists every row it was given, and redrawing those on each keystroke is felt.
function QuerySqlEditor() {
	const dispatch = useLedgerDispatch();
	const sql = useLedgerSelector(selectLedgerSql);

	return (
		<TextEditor
			language="sql"
			value={sql}
			onChange={(value) => dispatch(setLedgerSql(value))}
			fullscreenTitle="Ledger query"
			fileName="query.sql"
		/>
	);
}

export function QueryView() {
	const dispatch = useLedgerDispatch();
	const result = useLedgerSelector(selectLedgerQueryResult);
	const error = useLedgerSelector(selectLedgerQueryError);
	const tables = useLedgerSelector(selectLedgerTables);
	const detail = useLedgerSelector(selectLedgerDetail);

	// Shape alone, to match an open record detail back to a row of this result.
	// Whether the row is stored is settled when it is opened, not here.
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
					dispatch(openLedgerQueryRow({ record, cells }))
				}
			/>
		);
	}

	return (
		<div className="flex min-h-0 flex-1 flex-col">
			<QueryToolbar />

			<div className="h-48 shrink-0 border-b">
				<QuerySqlEditor />
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
