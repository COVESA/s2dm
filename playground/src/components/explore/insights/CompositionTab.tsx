import { EnumUsageCard } from "@insights-ui/components/EnumUsageCard";
import { FieldsByTypeCard } from "@insights-ui/components/FieldsByTypeCard";
import { ScalarDistributionCard } from "@insights-ui/components/ScalarDistributionCard";
import { TabsContent } from "@shared-ui/components/tabs";

export function CompositionTab() {
	return (
		<TabsContent
			value="composition"
			className="mt-0 flex min-h-0 flex-1 flex-col overflow-y-auto"
		>
			<div className="flex flex-col gap-4 p-4">
				<FieldsByTypeCard />
				<ScalarDistributionCard />
				<EnumUsageCard />
			</div>
		</TabsContent>
	);
}
