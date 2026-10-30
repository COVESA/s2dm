import { DocumentationCoverageCard } from "@insights-ui/components/DocumentationCoverageCard";
import { MissingUnitsCard } from "@insights-ui/components/MissingUnitsCard";
import { UnusedElementsCard } from "@insights-ui/components/UnusedElementsCard";
import { TabsContent } from "@shared-ui/components/tabs";

export function QualityTab() {
	return (
		<TabsContent
			value="quality"
			className="mt-0 flex min-h-0 flex-1 flex-col overflow-y-auto"
		>
			<div className="flex flex-col gap-4 p-4">
				<DocumentationCoverageCard />
				<UnusedElementsCard />
				<MissingUnitsCard />
			</div>
		</TabsContent>
	);
}
