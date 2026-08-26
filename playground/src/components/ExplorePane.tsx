import { closeInsightDetail } from "@insights-ui/state/insightDetailSlice";
import { ExplorerTab } from "@/components/explore/ExplorerTab";
import { InsightsTab } from "@/components/explore/InsightsTab";
import { LedgerTab } from "@/components/explore/LedgerTab";
import { Pane } from "@/components/Pane";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { selectHasSchema } from "@/store/schema/schemaSlice";
import {
	type ExploreTab,
	selectExploreTab,
	selectWorkspace,
	setExploreTab,
} from "@/store/ui/uiSlice";

type ExplorePaneProps = {
	position?: "none" | "left" | "center" | "right";
	className?: string;
};

export function ExplorePane({
	position = "center",
	className = "flex-1",
}: ExplorePaneProps) {
	const dispatch = useAppDispatch();
	const hasSchema = useAppSelector(selectHasSchema);
	const workspace = useAppSelector(selectWorkspace);
	const activeTab = useAppSelector(selectExploreTab);

	if (workspace === "ledger") {
		return (
			<Pane className={className} position={position}>
				<LedgerTab />
			</Pane>
		);
	}

	// Checked after the ledger workspace, which this must not block.
	if (!hasSchema) {
		return (
			<Pane className={className} position={position}>
				<div className="flex-1 flex items-center justify-center bg-background text-muted-foreground">
					<p>Import a schema to start</p>
				</div>
			</Pane>
		);
	}

	return (
		<Pane className={className} position={position}>
			<Tabs
				value={activeTab}
				onValueChange={(value) => {
					dispatch(setExploreTab(value as ExploreTab));
					dispatch(closeInsightDetail());
				}}
				className="flex h-full w-full min-h-0 flex-col"
			>
				<div className="my-2 px-4 flex items-center justify-center gap-2">
					<TabsList>
						<TabsTrigger value="explorer">Explorer</TabsTrigger>
						<TabsTrigger value="insights">Insights</TabsTrigger>
					</TabsList>
				</div>

				<ExplorerTab />
				<InsightsTab />
			</Tabs>
		</Pane>
	);
}
