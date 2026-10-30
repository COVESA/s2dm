import { CollapsibleSection } from "@insights-ui/components/CollapsibleSection";
import { EvidenceList } from "@insights-ui/components/EvidenceList";
import { ExpandableTypePathRow } from "@insights-ui/components/ExpandableTypePathRow";
import { RootTypesExcludedNote } from "@insights-ui/components/RootTypesExcludedNote";
import { selectCycleGroups } from "@insights-ui/selectors/relationships";
import { useInsightsSelector } from "@insights-ui/state/hooks";
import type { CyclicReference } from "@insights-ui/types/relationships";
import { formatPathSegments } from "@insights-ui/utils/formatPathSegments";
import { Heading } from "@shared-ui/components/heading";

function CycleRow({ cycle }: { cycle: CyclicReference }) {
	const segmentLabels = formatPathSegments(cycle.segments);

	return (
		<ExpandableTypePathRow
			segments={segmentLabels}
			metric={cycle.length}
			metricLabel="hops"
		/>
	);
}

export function CyclicReferencesDetail() {
	const cycleGroups = useInsightsSelector(selectCycleGroups);

	return (
		<div className="flex flex-col gap-6 text-sm text-card-foreground">
			<p className="text-muted-foreground">
				These are reference loops where following a chain of relationship fields
				leads back to a type already visited earlier in the chain.
			</p>

			<section className="flex flex-col gap-2">
				<Heading level="h3">Interpretation</Heading>
				<p className="text-muted-foreground">
					A cycle of length 1 is a self-reference: a type has a relationship
					field that points back to itself.
				</p>
				<p className="text-muted-foreground">
					A longer cycle passes through several types before returning to the
					type it started from.
				</p>
			</section>

			<section className="flex flex-col gap-2">
				<Heading level="h3">How it is calculated</Heading>
				<p className="text-muted-foreground">
					Traverse every container type along its relationship fields. When a
					traversal reaches a type already on the current path, the loop from
					that type back to itself is recorded as a cyclic reference.
				</p>
				<RootTypesExcludedNote />
			</section>

			<section className="flex flex-col gap-3">
				<Heading level="h3">Evidence</Heading>
				{cycleGroups.length === 0 && (
					<p className="text-muted-foreground">
						No cyclic references detected.
					</p>
				)}
				{cycleGroups.map((group) => (
					<CollapsibleSection
						key={group.length}
						title={`Length ${group.length}`}
						defaultCollapsed
					>
						<div className="flex flex-col gap-2 py-3">
							<EvidenceList>
								{group.cycles.map((cycle) => (
									<CycleRow
										key={formatPathSegments(cycle.segments).join(">")}
										cycle={cycle}
									/>
								))}
							</EvidenceList>
						</div>
					</CollapsibleSection>
				))}
			</section>
		</div>
	);
}
