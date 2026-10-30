import { CompositionSummaryCard } from "@insights-ui/components/CompositionSummaryCard";
import { ConceptsBreakdown } from "@insights-ui/components/ConceptsBreakdown";
import { QualitySummaryCard } from "@insights-ui/components/QualitySummaryCard";
import { TabsContent } from "@shared-ui/components/tabs";

export function OverviewTab() {
	return (
		<TabsContent
			value="overview"
			className="mt-0 flex min-h-0 flex-1 flex-col overflow-y-auto"
		>
			<div className="flex flex-col gap-4 p-4">
				<ConceptsBreakdown />
				<CompositionSummaryCard />
				<QualitySummaryCard />
			</div>
		</TabsContent>
	);
}
