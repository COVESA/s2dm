import { CollapsibleSection } from "@insights-ui/components/CollapsibleSection";
import { EvidenceList } from "@insights-ui/components/EvidenceList";
import { InsightLinkButton } from "@insights-ui/components/InsightLinkButton";
import { PathRow } from "@insights-ui/components/PathsByDepthDetail";
import { RootTypesExcludedNote } from "@insights-ui/components/RootTypesExcludedNote";
import { selectDepthGroups } from "@insights-ui/selectors/relationships";
import {
	useInsightsDispatch,
	useInsightsSelector,
} from "@insights-ui/state/hooks";
import { pushInsightDetail } from "@insights-ui/state/insightDetailSlice";
import { formatPathSegments } from "@insights-ui/utils/formatPathSegments";
import { Heading } from "@shared-ui/components/heading";

const PATHS_PER_GROUP = 3;

export function DeepestPathsDetail() {
	const dispatch = useInsightsDispatch();
	const depthGroups = useInsightsSelector(selectDepthGroups);

	return (
		<div className="flex flex-col gap-6 text-sm text-card-foreground">
			<p className="text-muted-foreground">
				These are the longest traversal paths created by fields that reference
				other object types.
			</p>

			<section className="flex flex-col gap-2">
				<Heading level="h3">Interpretation</Heading>
				<p className="text-muted-foreground">
					A path with depth 1 means that one container type A relates to another
					container type B, and B has no further relations to another type.
				</p>
				<p className="text-muted-foreground">
					The deepest path is the maximum number of hops found in the model.
				</p>
			</section>

			<section className="flex flex-col gap-2">
				<Heading level="h3">How it is calculated</Heading>
				<p className="text-muted-foreground">
					Traverse every container type as if it would be a root. Count the
					maximum number of type-to-type steps, and stop traversal when a cycle
					is detected.
				</p>
				<RootTypesExcludedNote />
			</section>

			<section className="flex flex-col gap-3">
				<Heading level="h3">Evidence</Heading>
				{depthGroups.length === 0 && (
					<p className="text-muted-foreground">No nested paths found.</p>
				)}
				{depthGroups.map((group) => (
					<CollapsibleSection
						key={group.depth}
						title={`Depth ${group.depth}`}
						defaultCollapsed
					>
						<div className="flex flex-col gap-2 py-3">
							<EvidenceList>
								{group.paths.slice(0, PATHS_PER_GROUP).map((path) => (
									<PathRow
										key={formatPathSegments(path.segments).join(">")}
										path={path}
									/>
								))}
							</EvidenceList>
							{group.paths.length > PATHS_PER_GROUP && (
								<InsightLinkButton
									label={`View all ${group.paths.length}`}
									className="mt-1"
									onClick={() =>
										dispatch(
											pushInsightDetail({
												kind: "pathsByDepth",
												depth: group.depth,
											}),
										)
									}
								/>
							)}
						</div>
					</CollapsibleSection>
				))}
			</section>
		</div>
	);
}
