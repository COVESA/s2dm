import { closeInsightDetail } from "@insights-ui/state/insightDetailSlice";
import { Tabs, TabsList, TabsTrigger } from "@shared-ui/components/tabs";
import { ExplorerTab } from "@/components/explore/ExplorerTab";
import { InsightsTab } from "@/components/explore/InsightsTab";
import { Pane } from "@/components/Pane";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { selectHasSchema } from "@/store/schema/schemaSlice";
import {
	type ExploreTab,
	selectExploreTab,
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
	const activeTab = useAppSelector(selectExploreTab);

	const handleTabChange = (value: string) => {
		dispatch(setExploreTab(value as ExploreTab));
		dispatch(closeInsightDetail());
	};

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
				onValueChange={handleTabChange}
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
