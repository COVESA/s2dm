import { Play } from "lucide-react";
import { LedgerResultsGrid } from "@/components/explore/ledger/LedgerResultsGrid";
import { TextEditor } from "@/components/TextEditor";
import { Button } from "@/components/ui/button";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { StatusBanner } from "@/components/ui/status-banner";
import { PREDEFINED_QUERIES } from "@/ledger/predefinedQueries";
import { matchResultTable } from "@/ledger/resultRecord";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	openLedgerDetail,
	runLedgerQuery,
	selectIsRunningLedgerQuery,
	selectLedgerDetail,
	selectLedgerQueryError,
	selectLedgerQueryResult,
	selectLedgerSql,
	selectLedgerTables,
	selectPredefinedQuery,
	selectPredefinedQueryLabel,
	setLedgerSql,
} from "@/store/ledger/ledgerSlice";

export function QueryView() {
	const dispatch = useAppDispatch();
	const sql = useAppSelector(selectLedgerSql);
	const result = useAppSelector(selectLedgerQueryResult);
	const isRunning = useAppSelector(selectIsRunningLedgerQuery);
	const error = useAppSelector(selectLedgerQueryError);
	const tables = useAppSelector(selectLedgerTables);
	const detail = useAppSelector(selectLedgerDetail);
	const predefinedQuery = useAppSelector(selectPredefinedQueryLabel);

	const selectedDescription = PREDEFINED_QUERIES.find(
		(query) => query.label === predefinedQuery,
	)?.description;
	// By column shape, not row count: whole records stay identifiable however
	// many of them the query returned.
	const recordTable = result ? matchResultTable(result.columns, tables) : null;

	const handlePredefined = (label: string) => {
		dispatch(selectPredefinedQuery(label));
		dispatch(runLedgerQuery());
	};

	let content: React.ReactNode;
	if (error) {
		content = (
			<StatusBanner variant="destructive" className="whitespace-pre-wrap">
				{error}
			</StatusBanner>
		);
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
				selectedRecord={
					// Only when the result is one identifiable table: a projection has
					// no identity, so matching by value would highlight unrelated rows.
					recordTable && detail?.table === recordTable ? detail.record : null
				}
				onRowClick={(record) =>
					dispatch(openLedgerDetail({ table: recordTable ?? "", record }))
				}
			/>
		);
	}

	return (
		<div className="flex min-h-0 flex-1 flex-col">
			<div className="flex flex-col gap-2 border-b px-6 py-3">
				<div className="flex flex-wrap items-center gap-3">
					<Select value={predefinedQuery} onValueChange={handlePredefined}>
						<SelectTrigger className="w-64">
							<SelectValue placeholder="Predefined queries">
								{predefinedQuery}
							</SelectValue>
						</SelectTrigger>
						<SelectContent>
							{PREDEFINED_QUERIES.map((query) => (
								<SelectItem key={query.label} value={query.label}>
									<span className="flex flex-col items-start">
										<span>{query.label}</span>
										<span className="text-xs text-muted-foreground">
											{query.description}
										</span>
									</span>
								</SelectItem>
							))}
						</SelectContent>
					</Select>

					<Button
						onClick={() => dispatch(runLedgerQuery())}
						disabled={!sql.trim()}
						loading={isRunning}
					>
						<Play className="h-4 w-4" />
						Run
					</Button>
				</div>

				{/* Always present so the toolbar keeps its height. */}
				<span
					className="block min-h-4 truncate text-muted-foreground text-xs"
					title={selectedDescription}
				>
					{selectedDescription}
				</span>
			</div>

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
