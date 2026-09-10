import { ExploreView } from "@ledger-ui/components/ExploreView";
import { QueryView } from "@ledger-ui/components/QueryView";
import { RawTablesView } from "@ledger-ui/components/RawTablesView";
import { useLedgerDispatch, useLedgerSelector } from "@ledger-ui/state/hooks";
import {
	type LedgerView,
	selectHasLedger,
	selectLedgerView,
	setLedgerView,
} from "@ledger-ui/state/ledgerSlice";
import { EmptyState } from "@/components/ui/empty-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function LedgerTab() {
	const dispatch = useLedgerDispatch();
	const hasLedger = useLedgerSelector(selectHasLedger);
	const view = useLedgerSelector(selectLedgerView);

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
