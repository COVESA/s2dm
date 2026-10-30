import { CollapsibleSection } from "@insights-ui/components/CollapsibleSection";
import { EvidenceList } from "@insights-ui/components/EvidenceList";
import { InsightLinkButton } from "@insights-ui/components/InsightLinkButton";
import { RootTypesExcludedNote } from "@insights-ui/components/RootTypesExcludedNote";
import { UnusedRow } from "@insights-ui/components/UnusedElementsListDetail";
import { selectUnusedByCategory } from "@insights-ui/selectors/quality";
import {
	useInsightsDispatch,
	useInsightsSelector,
} from "@insights-ui/state/hooks";
import { pushInsightDetail } from "@insights-ui/state/insightDetailSlice";
import { Heading } from "@shared-ui/components/heading";

const ELEMENTS_PER_CATEGORY = 3;

export function UnusedElementsDetail() {
	const dispatch = useInsightsDispatch();
	const unusedByCategory = useInsightsSelector(selectUnusedByCategory);

	return (
		<div className="flex flex-col gap-6 text-sm text-card-foreground">
			<p className="text-muted-foreground">
				Elements that are defined in the model but never referenced by any field
				or argument.
			</p>

			<section className="flex flex-col gap-2">
				<Heading level="h3">Interpretation</Heading>
				<p className="text-muted-foreground">
					Unused elements add noise to the model and may indicate dead
					definitions or wiring that was never completed.
				</p>
				<p className="text-muted-foreground">
					Keeping an unused element can be intentional, for example when it is
					reserved for future use. It does not necessarily imply an issue.
				</p>
			</section>

			<section className="flex flex-col gap-2">
				<Heading level="h3">How it is calculated</Heading>
				<p className="text-muted-foreground">
					A type is unused when nothing references it: no field, argument, union
					member, or interface implementation points to it. A directive is
					unused when it is defined but never applied to any element.
				</p>
				<RootTypesExcludedNote />
			</section>

			<section className="flex flex-col gap-3">
				<Heading level="h3">Evidence</Heading>
				<div className="flex flex-col gap-3">
					{unusedByCategory.length === 0 && (
						<p className="text-muted-foreground">No unused elements.</p>
					)}
					{unusedByCategory.map((group) => (
						<CollapsibleSection
							key={group.category}
							title={`${group.category} (${group.elements.length})`}
							defaultCollapsed
						>
							<div className="flex flex-col gap-2 py-3">
								<EvidenceList>
									{group.elements
										.slice(0, ELEMENTS_PER_CATEGORY)
										.map((element) => (
											<UnusedRow
												key={`${element.category}:${element.target}`}
												{...element}
											/>
										))}
								</EvidenceList>
								{group.elements.length > ELEMENTS_PER_CATEGORY && (
									<InsightLinkButton
										label={`View all ${group.elements.length}`}
										className="mt-1"
										onClick={() =>
											dispatch(
												pushInsightDetail({
													kind: "unusedList",
													category: group.category,
												}),
											)
										}
									/>
								)}
							</div>
						</CollapsibleSection>
					))}
				</div>
			</section>
		</div>
	);
}
