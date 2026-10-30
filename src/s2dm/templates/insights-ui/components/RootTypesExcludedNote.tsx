import { StatusBanner } from "@shared-ui/components/status-banner";

export function RootTypesExcludedNote() {
	return (
		<StatusBanner variant="info">
			<span className="font-medium">Note:</span> configured technical root types
			such as Query, Mutation, and Subscription may be excluded from
			domain-oriented counts.
		</StatusBanner>
	);
}
