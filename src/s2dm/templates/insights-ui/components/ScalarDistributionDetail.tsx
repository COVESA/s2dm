import { EvidenceList } from "@insights-ui/components/EvidenceList";
import { InsightLinkButton } from "@insights-ui/components/InsightLinkButton";
import { ScalarUsageRow } from "@insights-ui/components/ScalarDistributionListDetail";
import {
	selectScalarUsage,
	selectScalarUsageStats,
} from "@insights-ui/selectors/concepts";
import {
	useInsightsDispatch,
	useInsightsSelector,
} from "@insights-ui/state/hooks";
import { pushInsightDetail } from "@insights-ui/state/insightDetailSlice";
import { Heading } from "@shared-ui/components/heading";

export function ScalarDistributionDetail() {
	const dispatch = useInsightsDispatch();
	const scalarUsage = useInsightsSelector(selectScalarUsage);
	const stats = useInsightsSelector(selectScalarUsageStats);

	const scalarCount = stats?.scalarCount ?? 0;
	const topScalars = scalarUsage.slice(0, 5);
	const statRows = [
		{ label: "Distinct datatypes used", value: scalarCount },
		{ label: "Total scalar field usages", value: stats?.totalOccurrences ?? 0 },
		{ label: "Built-in scalars", value: stats?.builtinCount ?? 0 },
		{ label: "Custom scalars", value: stats?.customCount ?? 0 },
	];

	return (
		<div className="flex flex-col gap-6 text-sm text-card-foreground">
			<p className="text-muted-foreground">
				How often each datatype is used as a field's output type across the
				composed model, covering the built-in scalars and any custom-defined
				scalars.
			</p>

			<section className="flex flex-col gap-2">
				<Heading level="h3">Interpretation</Heading>
				<ul className="flex list-disc flex-col gap-2 pl-5 text-muted-foreground">
					<li>
						A high usage count means many fields carry that datatype; it is a
						core building block of the model.
					</li>
					<li>
						Built-in scalars are the GraphQL primitives (String, Int, Float,
						Boolean, ID). Custom scalars are datatypes declared in the schema.
					</li>
					<li>
						A rarely used custom scalar may deserve review to confirm it earns
						its place in the model.
					</li>
				</ul>
			</section>

			<section className="flex flex-col gap-2">
				<Heading level="h3">How it is calculated</Heading>
				<p className="text-muted-foreground">
					For every field declared on a container type (object, interface,
					input), resolve its named output type. When that type is a scalar,
					count one usage against it, then sort by usage count descending.
				</p>
			</section>

			<section className="flex flex-col gap-4">
				<Heading level="h3">Evidence</Heading>

				<div className="flex flex-col gap-2">
					{topScalars.length > 0 ? (
						<>
							<EvidenceList>
								{topScalars.map((scalar) => (
									<ScalarUsageRow key={scalar.name} {...scalar} />
								))}
							</EvidenceList>
							{scalarCount > topScalars.length && (
								<InsightLinkButton
									label={`View all ${scalarCount}`}
									className="mt-1"
									onClick={() =>
										dispatch(
											pushInsightDetail({ kind: "scalarDistributionList" }),
										)
									}
								/>
							)}
						</>
					) : (
						<p className="text-muted-foreground">No datatypes are used.</p>
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
		</div>
	);
}
