import { CollapsibleSection } from "@insights-ui/components/CollapsibleSection";
import { EvidenceList } from "@insights-ui/components/EvidenceList";
import { InsightLinkButton } from "@insights-ui/components/InsightLinkButton";
import { UndocumentedRow } from "@insights-ui/components/UndocumentedListDetail";
import { selectUndocumentedByKind } from "@insights-ui/selectors/coverage";
import {
	useInsightsDispatch,
	useInsightsSelector,
} from "@insights-ui/state/hooks";
import { pushInsightDetail } from "@insights-ui/state/insightDetailSlice";
import { Heading } from "@shared-ui/components/heading";

const ELEMENTS_PER_KIND = 3;

export function UndocumentedDetail() {
	const dispatch = useInsightsDispatch();
	const undocumentedByKind = useInsightsSelector(selectUndocumentedByKind);

	return (
		<div className="flex flex-col gap-6 text-sm text-card-foreground">
			<p className="text-muted-foreground">
				How much of the model is documented via doc-string descriptions, and how
				many elements do not contain a description.
			</p>

			<section className="flex flex-col gap-2">
				<Heading level="h3">Interpretation</Heading>
				<p className="text-muted-foreground">
					A low documentation coverage is undesired because some elements might
					not be self-explainable, and users would have a hard time
					understanding them.
				</p>
				<p className="text-muted-foreground">
					If an element is self-explainable, one might leave it without a
					description. Although 100% is ideal, not achieving it does not imply
					an issue.
				</p>
			</section>

			<section className="flex flex-col gap-2">
				<Heading level="h3">How it is calculated</Heading>
				<p className="text-muted-foreground">
					Check all eligible GraphQL elements and mark those without a
					description as undocumented. Count them and compute the percentage.
				</p>
				<ul className="flex list-disc flex-col gap-1 pl-5 text-muted-foreground">
					<li>
						Types = object types + interface types + input object types + union
						types + custom scalar types
					</li>
					<li>
						Fields = fields declared on object types, interfaces, and input
						object types
					</li>
					<li>Enums = enum type definitions</li>
					<li>Enum values = values declared within each enum</li>
					<li>
						Directives = custom directive definitions, excluding built-in
						directives such as @deprecated, @skip, and @include
					</li>
				</ul>
			</section>

			<section className="flex flex-col gap-3">
				<Heading level="h3">Evidence</Heading>
				<div className="flex flex-col gap-3">
					{undocumentedByKind.length === 0 && (
						<p className="text-muted-foreground">Everything is documented.</p>
					)}
					{undocumentedByKind.map((group) => (
						<CollapsibleSection
							key={group.kind}
							title={`${group.kind} (${group.elements.length})`}
							defaultCollapsed
						>
							<div className="flex flex-col gap-2 py-3">
								<EvidenceList>
									{group.elements.slice(0, ELEMENTS_PER_KIND).map((element) => (
										<UndocumentedRow
											key={`${element.kind}:${element.name}`}
											{...element}
										/>
									))}
								</EvidenceList>
								{group.elements.length > ELEMENTS_PER_KIND && (
									<InsightLinkButton
										label={`View all ${group.elements.length}`}
										className="mt-1"
										onClick={() =>
											dispatch(
												pushInsightDetail({
													kind: "undocumentedList",
													entityKind: group.kind,
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
