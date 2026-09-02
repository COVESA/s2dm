import { Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { PREDEFINED_QUERIES } from "@/ledger/predefinedQueries";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	applyPredefinedQuery,
	runLedgerQuery,
	selectIsRunningLedgerQuery,
	selectLedgerSql,
	selectPredefinedQueryLabel,
} from "@/store/ledger/ledgerSlice";

export function QueryToolbar() {
	const dispatch = useAppDispatch();
	const sql = useAppSelector(selectLedgerSql);
	const isRunning = useAppSelector(selectIsRunningLedgerQuery);
	const predefinedQuery = useAppSelector(selectPredefinedQueryLabel);
	const selectedDescription = PREDEFINED_QUERIES.find(
		(query) => query.label === predefinedQuery,
	)?.description;

	// Picking a preset runs it, so the result appears without a second click.
	const handlePredefined = (label: string) => {
		dispatch(applyPredefinedQuery(label));
		dispatch(runLedgerQuery());
	};

	return (
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
	);
}
