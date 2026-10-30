import { EnumUsageRow } from "@insights-ui/components/EnumUsageListDetail";
import { EvidenceList } from "@insights-ui/components/EvidenceList";
import { InsightLinkButton } from "@insights-ui/components/InsightLinkButton";
import {
	selectEnumUsage,
	selectEnumUsageStats,
} from "@insights-ui/selectors/concepts";
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

export function EnumUsageDetail() {
	const dispatch = useInsightsDispatch();
	const enumUsage = useInsightsSelector(selectEnumUsage);
	const stats = useInsightsSelector(selectEnumUsageStats);

	const mostUsed = stats?.mostUsed ?? null;
	const leastUsed = stats?.leastUsed ?? null;
	const usedCount = stats?.usedCount ?? 0;
	const unusedCount = stats?.unusedCount ?? 0;
	const topEnums = enumUsage.slice(0, 5);
	const statRows = [
		{ label: "Enums used", value: usedCount },
		{ label: "Total enum usages", value: stats?.totalOccurrences ?? 0 },
		{ label: "Most used", value: mostUsed ? mostUsed.name : "—" },
		{ label: "Least used", value: leastUsed ? leastUsed.name : "—" },
		{ label: "Unused enums", value: unusedCount },
	];

	const openUnusedEnums = () => {
		dispatch(setInsightsSubTab("quality"));
		dispatch(openInsightDetail({ kind: "unused" }));
	};

	return (
		<div className="flex flex-col gap-6 text-sm text-card-foreground">
			<p className="text-muted-foreground">
				How often each enum is used across the composed model — as a field's
				output type, a field argument, or a directive argument. Enums never used
				this way are surfaced separately as unused elements.
			</p>

			<section className="flex flex-col gap-2">
				<Heading level="h3">Interpretation</Heading>
				<ul className="flex list-disc flex-col gap-2 pl-5 text-muted-foreground">
					<li>
						A high usage count means many places reference that enum; it is a
						core vocabulary of the model.
					</li>
					<li>
						The least used enum still earns its place, but a rarely used enum
						may deserve review.
					</li>
					<li>
						Unused enums are declared but never referenced by any field or
						argument. Review them in the Quality tab.
					</li>
				</ul>
			</section>

			<section className="flex flex-col gap-2">
				<Heading level="h3">How it is calculated</Heading>
				<p className="text-muted-foreground">
					For every field declared on a container type (object, interface,
					input), resolve its named output type and the type of each of its
					arguments; do the same for every directive's arguments. Count one
					usage for each that resolves to an enum, then sort by usage count
					descending.
				</p>
			</section>

			<section className="flex flex-col gap-4">
				<Heading level="h3">Evidence</Heading>

				<div className="flex flex-col gap-2">
					{topEnums.length > 0 ? (
						<>
							<EvidenceList>
								{topEnums.map((entry) => (
									<EnumUsageRow key={entry.name} {...entry} />
								))}
							</EvidenceList>
							{usedCount > topEnums.length && (
								<InsightLinkButton
									label={`View all ${usedCount}`}
									className="mt-1"
									onClick={() =>
										dispatch(pushInsightDetail({ kind: "enumUsageList" }))
									}
								/>
							)}
						</>
					) : (
						<p className="text-muted-foreground">No enums are used.</p>
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

				{unusedCount > 0 && (
					<InsightLinkButton
						label="View unused enums in Quality"
						onClick={openUnusedEnums}
					/>
				)}
			</section>
		</div>
	);
}
