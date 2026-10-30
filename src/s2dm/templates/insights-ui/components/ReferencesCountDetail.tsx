import { EvidenceList } from "@insights-ui/components/EvidenceList";
import { InsightLinkButton } from "@insights-ui/components/InsightLinkButton";
import { ReferenceCountRow } from "@insights-ui/components/ReferencesCountListDetail";
import { RootTypesExcludedNote } from "@insights-ui/components/RootTypesExcludedNote";
import {
	selectReferenceCountStats,
	selectReferenceCounts,
} from "@insights-ui/selectors/relationships";
import {
	useInsightsDispatch,
	useInsightsSelector,
} from "@insights-ui/state/hooks";
import {
	openInsightDetail,
	pushInsightDetail,
	setInsightsSubTab,
} from "@insights-ui/state/insightDetailSlice";
import { Heading } from "@shared-ui/components/heading";

export function ReferencesCountDetail() {
	const dispatch = useInsightsDispatch();
	const referenceCounts = useInsightsSelector(selectReferenceCounts);
	const stats = useInsightsSelector(selectReferenceCountStats);

	const mostReferenced = stats?.mostReferenced ?? null;
	const leastReferenced = stats?.leastReferenced ?? null;
	const referencedCount = stats?.referencedCount ?? 0;
	const unusedCount = stats?.unusedCount ?? 0;
	const topReferences = referenceCounts.slice(0, 5);
	const statRows = [
		{ label: "Types referenced", value: referencedCount },
		{ label: "Total references", value: stats?.totalReferences ?? 0 },
		{
			label: "Most referenced",
			value: mostReferenced ? mostReferenced.name : "—",
		},
		{
			label: "Least referenced",
			value: leastReferenced ? leastReferenced.name : "—",
		},
		{ label: "Unused elements", value: unusedCount },
	];

	const openUnusedElements = () => {
		dispatch(setInsightsSubTab("quality"));
		dispatch(openInsightDetail({ kind: "unused" }));
	};

	const openEnumUsage = () => {
		dispatch(setInsightsSubTab("composition"));
		dispatch(openInsightDetail({ kind: "enumUsage" }));
	};

	return (
		<div className="flex flex-col gap-6 text-sm text-card-foreground">
			<p className="text-muted-foreground">
				How often each type is referenced across the composed model. A type is
				counted wherever a field, argument, union member, or interface
				implementation points to it. Scalars and enums are excluded here — they
				have their own Scalar Distribution and Enum Usage cards.
			</p>

			<section className="flex flex-col gap-2">
				<Heading level="h3">Interpretation</Heading>
				<ul className="flex list-disc flex-col gap-2 pl-5 text-muted-foreground">
					<li>
						A high count means the type is a load-bearing part of the model that
						many other elements depend on.
					</li>
					<li>
						The least referenced element still earns its place, but a rarely
						referenced one may deserve review.
					</li>
					<li>
						Unused elements are declared but never referenced. Review them in
						the Quality tab.
					</li>
				</ul>
			</section>

			<section className="flex flex-col gap-2">
				<Heading level="h3">How it is calculated</Heading>
				<p className="text-muted-foreground">
					For every field, argument, union member, and interface implementation,
					resolve the type it points to and count one reference against it.
					Scalars and enums are excluded, then results are sorted by count
					descending.
				</p>
				<RootTypesExcludedNote />
			</section>

			<section className="flex flex-col gap-4">
				<Heading level="h3">Evidence</Heading>

				<div className="flex flex-col gap-2">
					{topReferences.length > 0 ? (
						<>
							<EvidenceList>
								{topReferences.map((entry) => (
									<ReferenceCountRow key={entry.name} {...entry} />
								))}
							</EvidenceList>
							{referencedCount > topReferences.length && (
								<InsightLinkButton
									label={`View all ${referencedCount}`}
									className="mt-1"
									onClick={() =>
										dispatch(pushInsightDetail({ kind: "referencesList" }))
									}
								/>
							)}
						</>
					) : (
						<p className="text-muted-foreground">No types are referenced.</p>
					)}
				</div>

				<div className="flex flex-col gap-2">
					<Heading level="h4">Stats</Heading>
					<ul className="flex list-disc flex-col gap-1 pl-5 text-muted-foreground">
						{statRows.map((stat) => (
							<li key={stat.label}>
								{stat.label}:{" "}
								<span className="font-semibold text-card-foreground">
									{stat.value}
								</span>
							</li>
						))}
					</ul>
				</div>
			</section>

			<section className="flex flex-col gap-2">
				<Heading level="h3">Actions</Heading>
				<div className="flex flex-col items-start gap-2">
					<InsightLinkButton label="View enum usage" onClick={openEnumUsage} />
					{unusedCount > 0 && (
						<InsightLinkButton
							label="View unused elements in Quality"
							onClick={openUnusedElements}
						/>
					)}
				</div>
			</section>
		</div>
	);
}
