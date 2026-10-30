import {
	type InsightsSubTab,
	selectInsightsSubTab,
	setInsightsSubTab,
} from "@insights-ui/state/insightDetailSlice";
import {
	fetchInsights,
	selectInsightsConcepts,
	selectInsightsCoverage,
	selectInsightsError,
	selectInsightsRelationships,
	selectIsLoadingInsights,
} from "@insights-ui/state/insightsSlice";
import { Button } from "@shared-ui/components/button";
import { StatusBanner } from "@shared-ui/components/status-banner";
import {
	Tabs,
	TabsContent,
	TabsList,
	TabsTrigger,
} from "@shared-ui/components/tabs";
import { Loader2 } from "lucide-react";
import { useEffect, useRef } from "react";
import { CompositionTab } from "@/components/explore/insights/CompositionTab";
import { OverviewTab } from "@/components/explore/insights/OverviewTab";
import { QualityTab } from "@/components/explore/insights/QualityTab";
import { RelationshipsTab } from "@/components/explore/insights/RelationshipsTab";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { selectFilteredSchema } from "@/store/schema/schemaSlice";
import { selectExploreTab } from "@/store/ui/uiSlice";

export function InsightsTab() {
	const dispatch = useAppDispatch();
	const activeSubTab = useAppSelector(selectInsightsSubTab) ?? "overview";
	const activeTab = useAppSelector(selectExploreTab);
	const filteredSchema = useAppSelector(selectFilteredSchema);
	const concepts = useAppSelector(selectInsightsConcepts);
	const relationships = useAppSelector(selectInsightsRelationships);
	const coverage = useAppSelector(selectInsightsCoverage);
	const isLoading = useAppSelector(selectIsLoadingInsights);
	const error = useAppSelector(selectInsightsError);
	const fetchedSchema = useRef<string | null>(null);

	useEffect(() => {
		if (activeTab !== "insights") {
			return;
		}
		if (filteredSchema.trim().length === 0) {
			return;
		}
		if (fetchedSchema.current === filteredSchema) {
			return;
		}
		fetchedSchema.current = filteredSchema;
		dispatch(fetchInsights());
	}, [activeTab, filteredSchema, dispatch]);

	const handleSubTabChange = (value: string) => {
		dispatch(setInsightsSubTab(value as InsightsSubTab));
	};

	const hasAllData =
		concepts !== null && relationships !== null && coverage !== null;

	let content: React.ReactNode;
	if (error) {
		content = (
			<div className="p-4">
				<StatusBanner variant="destructive" className="whitespace-pre-wrap">
					<div className="flex items-center justify-between gap-3">
						<span>{error}</span>
						<Button
							type={"button"}
							variant="outline"
							size="sm"
							onClick={() => dispatch(fetchInsights())}
						>
							Retry
						</Button>
					</div>
				</StatusBanner>
			</div>
		);
	} else if (isLoading || !hasAllData) {
		content = (
			<div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
				<Loader2 className="h-6 w-6 animate-spin" />
				<p>Computing insights…</p>
			</div>
		);
	} else {
		content = (
			<Tabs
				value={activeSubTab}
				onValueChange={handleSubTabChange}
				className="flex h-full w-full min-h-0 flex-col"
			>
				<div className="my-2 px-4 flex items-center justify-center gap-2">
					<TabsList>
						<TabsTrigger value="overview">Overview</TabsTrigger>
						<TabsTrigger value="composition">Composition</TabsTrigger>
						<TabsTrigger value="relationships">Relationships</TabsTrigger>
						<TabsTrigger value="quality">Quality</TabsTrigger>
					</TabsList>
				</div>

				<OverviewTab />
				<CompositionTab />
				<RelationshipsTab />
				<QualityTab />
			</Tabs>
		);
	}

	return (
		<TabsContent value="insights" className="mt-0 flex min-h-0 flex-1 flex-col">
			{content}
		</TabsContent>
	);
}
