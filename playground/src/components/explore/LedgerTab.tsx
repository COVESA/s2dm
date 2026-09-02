import { ExploreView } from "@/components/explore/ledger/ExploreView";
import { QueryView } from "@/components/explore/ledger/QueryView";
import { RawTablesView } from "@/components/explore/ledger/RawTablesView";
import { EmptyState } from "@/components/ui/empty-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	type LedgerView,
	selectHasLedger,
	selectLedgerView,
	setLedgerView,
} from "@/store/ledger/ledgerSlice";

export function LedgerTab() {
	const dispatch = useAppDispatch();
	const hasLedger = useAppSelector(selectHasLedger);
	const view = useAppSelector(selectLedgerView);

	if (!hasLedger) {
		return <EmptyState title="Load a ledger database to start" />;
	}

	return (
		<Tabs
			value={view}
			onValueChange={(value) => dispatch(setLedgerView(value as LedgerView))}
			className="flex min-h-0 flex-1 flex-col"
		>
			<div className="my-2 flex items-center justify-center px-4">
				<TabsList>
					<TabsTrigger value="raw">Raw Tables</TabsTrigger>
					<TabsTrigger value="explore">Explore</TabsTrigger>
					<TabsTrigger value="query">Query</TabsTrigger>
				</TabsList>
			</div>

			<TabsContent value="raw" className="mt-0 flex min-h-0 flex-1 flex-col">
				<RawTablesView />
			</TabsContent>
			<TabsContent
				value="explore"
				className="mt-0 flex min-h-0 flex-1 flex-col"
			>
				<ExploreView />
			</TabsContent>
			<TabsContent value="query" className="mt-0 flex min-h-0 flex-1 flex-col">
				<QueryView />
			</TabsContent>
		</Tabs>
	);
}
