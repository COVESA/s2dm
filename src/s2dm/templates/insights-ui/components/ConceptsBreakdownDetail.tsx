import { CollapsibleSection } from "@insights-ui/components/CollapsibleSection";
import { EnumRow } from "@insights-ui/components/EnumsDetail";
import { EvidenceList } from "@insights-ui/components/EvidenceList";
import { EvidenceRow } from "@insights-ui/components/EvidenceRow";
import { FieldTypeRow } from "@insights-ui/components/FieldsByKindDetail";
import type { GraphQLConcept } from "@insights-ui/components/graphqlConceptStyles";
import { InsightLinkButton } from "@insights-ui/components/InsightLinkButton";
import { TypePathBreadcrumb } from "@insights-ui/components/TypePathBreadcrumb";
import {
	selectConceptMembers,
	selectEnums,
	selectLeafFields,
	selectRelationshipFields,
} from "@insights-ui/selectors/concepts";
import {
	useInsightsDispatch,
	useInsightsSelector,
} from "@insights-ui/state/hooks";
import { pushInsightDetail } from "@insights-ui/state/insightDetailSlice";
import { Heading } from "@shared-ui/components/heading";
import type { ReactNode } from "react";

const SAMPLE_SIZE = 3;

function EvidenceSubsection({
	title,
	children,
}: {
	title: string;
	children: ReactNode;
}) {
	return (
		<div className="flex flex-col gap-2">
			<Heading level="h4">{title}</Heading>
			{children}
		</div>
	);
}

function ConceptSampleSection({
	title,
	sample,
	totalCount,
	concept,
	emptyMessage,
}: {
	title: string;
	sample: string[];
	totalCount: number;
	concept: GraphQLConcept;
	emptyMessage?: string;
}) {
	const dispatch = useInsightsDispatch();

	if (sample.length === 0 && emptyMessage) {
		return (
			<EvidenceSubsection title={title}>
				<p className="text-muted-foreground">{emptyMessage}</p>
			</EvidenceSubsection>
		);
	}

	return (
		<EvidenceSubsection title={title}>
			<EvidenceList>
				{sample.map((name) => (
					<li key={name}>
						<EvidenceRow>
							<TypePathBreadcrumb segments={[name]} truncate={false} />
						</EvidenceRow>
					</li>
				))}
			</EvidenceList>
			{totalCount > sample.length && (
				<InsightLinkButton
					label={`View all ${totalCount}`}
					className="mt-1"
					onClick={() =>
						dispatch(pushInsightDetail({ kind: "conceptDetails", concept }))
					}
				/>
			)}
		</EvidenceSubsection>
	);
}

export function ConceptsBreakdownDetail() {
	const dispatch = useInsightsDispatch();
	const members = useInsightsSelector(selectConceptMembers);
	const leafFields = useInsightsSelector(selectLeafFields);
	const relationshipFields = useInsightsSelector(selectRelationshipFields);
	const enums = useInsightsSelector(selectEnums);

	const objectMembers = members?.object ?? [];
	const interfaceMembers = members?.interface ?? [];
	const inputMembers = members?.input ?? [];
	const objectSample = objectMembers.slice(0, SAMPLE_SIZE);
	const interfaceSample = interfaceMembers.slice(0, SAMPLE_SIZE);
	const inputSample = inputMembers.slice(0, SAMPLE_SIZE);
	const leafSample = leafFields.slice(0, SAMPLE_SIZE);
	const relationshipSample = relationshipFields.slice(0, SAMPLE_SIZE);
	let enumSample: { name: string; values: number; rank: string }[] = [];
	if (enums.length > 0) {
		enumSample = [
			{ ...enums[0], rank: "Largest" },
			{ ...enums[Math.floor(enums.length / 2)], rank: "Median" },
			{ ...enums[enums.length - 1], rank: "Smallest" },
		];
	}

	return (
		<div className="flex flex-col gap-6 text-sm text-card-foreground">
			<p className="text-muted-foreground">
				Count of the number of elements found in the current composed model,
				separated as Field Container Types, Fields and Enums.
			</p>

			<section className="flex flex-col gap-2">
				<Heading level="h3">Interpretation</Heading>
				<ul className="flex list-disc flex-col gap-2 pl-5 text-muted-foreground">
					<li>
						<span className="font-medium text-card-foreground">
							Field Container Types
						</span>{" "}
						— structures that contain fields. Think of them as the entities,
						features of interest, or classes that belong to the domain.
					</li>
					<li>
						<span className="font-medium text-card-foreground">Fields</span> —
						properties specified inside container types. Think of them as the
						aspects that characterize the container types.
						<ul className="mt-2 flex list-disc flex-col gap-1 pl-5">
							<li>
								<span className="font-medium text-card-foreground">
									Leaf fields
								</span>{" "}
								— fields whose output types are scalars (e.g. String, Boolean).
							</li>
							<li>
								<span className="font-medium text-card-foreground">
									Relationship fields
								</span>{" "}
								— fields whose output type is another type.
							</li>
							<li>
								<span className="font-medium text-card-foreground">
									Input fields
								</span>{" "}
								— fields declared on input object types.
							</li>
						</ul>
					</li>
					<li>
						<span className="font-medium text-card-foreground">Enums</span> —
						set of controlled terms.
					</li>
				</ul>
			</section>

			<section className="flex flex-col gap-2">
				<Heading level="h3">How it is calculated</Heading>
				<p className="text-muted-foreground">
					Count GraphQL definitions and fields from the composed schema:
				</p>
				<ul className="flex list-disc flex-col gap-1 pl-5 text-muted-foreground">
					<li>
						Field container types = object types + interface types + input
						object types
					</li>
					<li>
						Fields = fields declared on object types, interfaces, and input
						object types
					</li>
					<li>Enums = enum type definitions</li>
				</ul>
			</section>

			<section className="flex flex-col gap-3">
				<Heading level="h3">Evidence</Heading>

				<CollapsibleSection title="Field Container Types" defaultCollapsed>
					<div className="flex flex-col gap-4 py-3">
						<ConceptSampleSection
							title="Object types"
							sample={objectSample}
							totalCount={objectMembers.length}
							concept="object"
							emptyMessage="No object types in this schema."
						/>

						<ConceptSampleSection
							title="Interface types"
							sample={interfaceSample}
							totalCount={interfaceMembers.length}
							concept="interface"
							emptyMessage="No interface types in this schema."
						/>

						<ConceptSampleSection
							title="Input types"
							sample={inputSample}
							totalCount={inputMembers.length}
							concept="input"
							emptyMessage="No input types in this schema."
						/>
					</div>
				</CollapsibleSection>

				<CollapsibleSection title="Fields" defaultCollapsed>
					<div className="flex flex-col gap-4 py-3">
						<EvidenceSubsection title="Leaf fields">
							{leafFields.length > 0 ? (
								<>
									<EvidenceList>
										{leafSample.map((entry) => (
											<FieldTypeRow key={entry.field} {...entry} />
										))}
									</EvidenceList>
									{leafFields.length > leafSample.length && (
										<InsightLinkButton
											label={`View all ${leafFields.length}`}
											className="mt-1"
											onClick={() =>
												dispatch(
													pushInsightDetail({
														kind: "fieldsByKind",
														fieldKind: "leaf",
													}),
												)
											}
										/>
									)}
								</>
							) : (
								<p className="text-muted-foreground">
									No leaf fields in this schema.
								</p>
							)}
						</EvidenceSubsection>

						<EvidenceSubsection title="Relationship fields">
							{relationshipFields.length > 0 ? (
								<>
									<EvidenceList>
										{relationshipSample.map((entry) => (
											<FieldTypeRow key={entry.field} {...entry} />
										))}
									</EvidenceList>
									{relationshipFields.length > relationshipSample.length && (
										<InsightLinkButton
											label={`View all ${relationshipFields.length}`}
											className="mt-1"
											onClick={() =>
												dispatch(
													pushInsightDetail({
														kind: "fieldsByKind",
														fieldKind: "relationship",
													}),
												)
											}
										/>
									)}
								</>
							) : (
								<p className="text-muted-foreground">
									No relationship fields in this schema.
								</p>
							)}
						</EvidenceSubsection>
					</div>
				</CollapsibleSection>

				<CollapsibleSection title="Enums" defaultCollapsed>
					<div className="flex flex-col gap-2 py-3">
						{enums.length > 0 ? (
							<>
								<EvidenceList>
									{enumSample.map((entry) => (
										<EnumRow key={`${entry.name}:${entry.rank}`} {...entry} />
									))}
								</EvidenceList>
								<InsightLinkButton
									label={`View all ${enums.length}`}
									className="mt-1"
									onClick={() =>
										dispatch(pushInsightDetail({ kind: "enumsList" }))
									}
								/>
							</>
						) : (
							<p className="text-muted-foreground">No enums in this schema.</p>
						)}
					</div>
				</CollapsibleSection>
			</section>

			<section className="flex flex-col gap-2">
				<Heading level="h3">Actions</Heading>
				<InsightLinkButton label="Related actions" />
			</section>
		</div>
	);
}
