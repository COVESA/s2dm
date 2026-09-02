import { ArrowRight } from "lucide-react";
import pluralize from "pluralize";
import { LedgerResultsGrid } from "@/components/explore/ledger/LedgerResultsGrid";
import { LedgerSearchInput } from "@/components/explore/ledger/LedgerSearchInput";
import { LedgerErrorBanner } from "@/components/ledger/LedgerErrorBanner";
import { Button } from "@/components/ui/button";
import { capitalise } from "@/ledger/recordLabel";
import { recordValues } from "@/ledger/resultRow";
import type { LedgerSearchMatch } from "@/ledger/types";
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

	const selectedValuesIn = (match: LedgerSearchMatch) =>
		detail?.kind === "row" && detail.table === match.table
			? recordValues(detail.record, match.result.columns)
			: null;

	let content: React.ReactNode;
	if (error) {
		content = <LedgerErrorBanner>{error}</LedgerErrorBanner>;
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
					{pluralize("table", matches.length)}
				</p>

				{matches.map((match) => {
					const shown = match.result.rows.length;
					const hasMore = match.total > shown;
					const countLabel = hasMore
						? `${shown} of ${match.total} matching`
						: `${match.total} matching`;
					return (
						<section key={match.table} className="flex flex-col gap-2">
							<div className="flex items-center justify-between gap-2">
								<div className="flex items-baseline gap-2">
									<h3 className="font-semibold">{capitalise(match.table)}</h3>
									<span className="font-mono text-xs text-muted-foreground">
										{countLabel}
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
								sortable={false}
								containerClassName="max-h-96"
								selectedValues={selectedValuesIn(match)}
								onRowClick={(record) =>
									dispatch(
										openLedgerDetail({
											kind: "row",
											table: match.table,
											record,
										}),
									)
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
				<LedgerSearchInput
					value={query}
					onChange={(value) => dispatch(setExploreQuery(value))}
					label="Search the ledger"
				/>
			</div>

			<div className="flex flex-1 flex-col overflow-auto px-6 py-4">
				{content}
			</div>
		</div>
	);
}
