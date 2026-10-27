import { CyclicReferencesCard } from "@insights-ui/components/CyclicReferencesCard";
import { DeepestPathsCard } from "@insights-ui/components/DeepestPathsCard";
import { ReferencesCountCard } from "@insights-ui/components/ReferencesCountCard";
import { TabsContent } from "@shared-ui/components/tabs";

export function RelationshipsTab() {
	return (
		<TabsContent
			value="relationships"
			className="mt-0 flex min-h-0 flex-1 flex-col overflow-y-auto"
		>
			<div className="grid grid-cols-1 gap-4 p-4">
				<ReferencesCountCard />
				<DeepestPathsCard />
				<CyclicReferencesCard />
			</div>
		</TabsContent>
	);
}
