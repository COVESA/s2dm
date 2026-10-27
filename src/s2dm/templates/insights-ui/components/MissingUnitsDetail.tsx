import { EvidenceList } from "@insights-ui/components/EvidenceList";
import { InsightLinkButton } from "@insights-ui/components/InsightLinkButton";
import { MissingUnitRow } from "@insights-ui/components/MissingUnitsListDetail";
import {
	selectMissingUnits,
	selectMissingUnitsStats,
} from "@insights-ui/selectors/quality";
import {
	useInsightsDispatch,
	useInsightsSelector,
} from "@insights-ui/state/hooks";
import { pushInsightDetail } from "@insights-ui/state/insightDetailSlice";
import { Heading } from "@shared-ui/components/heading";

const PREVIEW_COUNT = 5;

export function MissingUnitsDetail() {
	const dispatch = useInsightsDispatch();
	const missingUnits = useInsightsSelector(selectMissingUnits);
	const stats = useInsightsSelector(selectMissingUnitsStats);

	const count = stats?.count ?? 0;
	const preview = missingUnits.slice(0, PREVIEW_COUNT);

	return (
		<div className="flex flex-col gap-6 text-sm text-card-foreground">
			<p className="text-muted-foreground">
				Scalar-typed fields that do not declare a <code>unit</code> argument. A
				field measuring a physical quantity usually names its unit, so a missing
				one is worth a glance.
			</p>

			<section className="flex flex-col gap-2">
				<Heading level="h3">Interpretation</Heading>
				<p className="text-muted-foreground">
					This is a sanity check, not a modeling requirement. Many scalar fields
					legitimately have no unit — counts, ratios, and identifiers among them
					— so a flagged field is a prompt to confirm, not an error to fix.
				</p>
			</section>

			<section className="flex flex-col gap-2">
				<Heading level="h3">How it is calculated</Heading>
				<p className="text-muted-foreground">
					Every field whose output type is a scalar is a candidate, including
					custom scalars. Fields typed by String, ID, or Boolean carry no
					measurable quantity and are skipped. A candidate passes when it
					declares a <code>unit</code> argument; otherwise it is listed here.
				</p>
			</section>

			<section className="flex flex-col gap-4">
				<Heading level="h3">Evidence</Heading>
				{preview.length > 0 ? (
					<div className="flex flex-col gap-2">
						<EvidenceList>
							{preview.map((element) => (
								<MissingUnitRow key={element.target} {...element} />
							))}
						</EvidenceList>
						{count > preview.length && (
							<InsightLinkButton
								label={`View all ${count}`}
								className="mt-1"
								onClick={() =>
									dispatch(pushInsightDetail({ kind: "missingUnitsList" }))
								}
							/>
						)}
					</div>
				) : (
					<p className="text-muted-foreground">
						Every measurable field declares a unit.
					</p>
				)}
			</section>
		</div>
	);
}
