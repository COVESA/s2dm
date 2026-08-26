import { ArrowRight, Search } from "lucide-react";
import { LedgerResultsGrid } from "@/components/explore/ledger/LedgerResultsGrid";
import { SearchOptionToggles } from "@/components/explore/ledger/SearchOptionToggles";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatusBanner } from "@/components/ui/status-banner";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	openLedgerDetail,
	openTableWithSearch,
	selectExploreError,
	selectExploreMatches,
	selectExploreQuery,
	selectHasExplored,
	selectIsExploring,
	selectLedgerDetail,
	setExploreQuery,
} from "@/store/ledger/ledgerSlice";

export function ExploreView() {
	const dispatch = useAppDispatch();
	const query = useAppSelector(selectExploreQuery);
	const matches = useAppSelector(selectExploreMatches);
	const hasExplored = useAppSelector(selectHasExplored);
	const isExploring = useAppSelector(selectIsExploring);
	const error = useAppSelector(selectExploreError);
	const detail = useAppSelector(selectLedgerDetail);

	const totalRows = matches.reduce((total, match) => total + match.total, 0);

	let content: React.ReactNode;
	if (error) {
		content = (
			<StatusBanner variant="destructive" className="whitespace-pre-wrap">
				{error}
			</StatusBanner>
		);
	} else if (!query.trim()) {
		content = (
			<div className="flex flex-1 items-center justify-center text-muted-foreground">
				<p>
					Search the whole ledger by label, kind, status, URI, serial or
					instance
				</p>
			</div>
		);
	} else if (isExploring || !hasExplored) {
		// Also before the first result lands, when there is nothing to report yet.
		content = <p className="text-sm text-muted-foreground">Searching…</p>;
	} else if (matches.length === 0) {
		content = (
			<p className="text-sm text-muted-foreground">
				Nothing in this ledger matches “{query.trim()}”
			</p>
		);
	} else {
		content = (
			<div className="flex flex-col gap-6">
				<p className="text-muted-foreground text-sm">
					{totalRows} records in {matches.length}{" "}
					{matches.length === 1 ? "table" : "tables"}
				</p>

				{matches.map((match) => {
					const shown = match.result.rows.length;
					const hasMore = match.total > shown;
					return (
						<section key={match.table} className="flex flex-col gap-2">
							<div className="flex items-center justify-between gap-2">
								<div className="flex items-baseline gap-2">
									<h3 className="font-semibold capitalize">{match.table}</h3>
									<span className="font-mono text-xs text-muted-foreground">
										{hasMore
											? `${shown} of ${match.total} matching`
											: `${match.total} matching`}
									</span>
								</div>
								{hasMore && (
									<Button
										variant="outline"
										size="sm"
										onClick={() =>
											dispatch(
												openTableWithSearch({
													table: match.table,
													search: query.trim(),
												}),
											)
										}
									>
										Display all {match.total}
										<ArrowRight className="h-4 w-4" />
									</Button>
								)}
							</div>
							<LedgerResultsGrid
								result={match.result}
								containerClassName="max-h-96"
								selectedRecord={
									detail?.table === match.table ? detail.record : null
								}
								onRowClick={(record) =>
									dispatch(openLedgerDetail({ table: match.table, record }))
								}
							/>
						</section>
					);
				})}
			</div>
		);
	}

	return (
		<div className="flex min-h-0 flex-1 flex-col">
			<div className="flex flex-col gap-3 border-b px-6 py-3">
				<div className="relative w-full">
					<Search className="absolute top-1/2 left-2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
					<Input
						value={query}
						onChange={(event) => dispatch(setExploreQuery(event.target.value))}
						placeholder="Search the ledger"
						className="pl-8 pr-24"
						aria-label="Search the ledger"
					/>
					<SearchOptionToggles />
				</div>
			</div>

			<div className="flex flex-1 flex-col overflow-auto px-6 py-4">
				{content}
			</div>
		</div>
	);
}
