import type { PropSidebar } from "@docusaurus/plugin-content-docs";
import { DocsSidebarProvider } from "@docusaurus/plugin-content-docs/client";
import { useHistory, useLocation } from "@docusaurus/router";
import {
	HtmlClassNameProvider,
	ThemeClassNames,
} from "@docusaurus/theme-common";
import useBaseUrl from "@docusaurus/useBaseUrl";
import { CompositionSummaryCard } from "@insights-ui/components/CompositionSummaryCard";
import { ConceptsBreakdown } from "@insights-ui/components/ConceptsBreakdown";
import { CyclicReferencesCard } from "@insights-ui/components/CyclicReferencesCard";
import { DeepestPathsCard } from "@insights-ui/components/DeepestPathsCard";
import { DocumentationCoverageCard } from "@insights-ui/components/DocumentationCoverageCard";
import { EnumUsageCard } from "@insights-ui/components/EnumUsageCard";
import { FieldsByTypeCard } from "@insights-ui/components/FieldsByTypeCard";
import { MissingUnitsCard } from "@insights-ui/components/MissingUnitsCard";
import { QualitySummaryCard } from "@insights-ui/components/QualitySummaryCard";
import { ReferencesCountCard } from "@insights-ui/components/ReferencesCountCard";
import { ScalarDistributionCard } from "@insights-ui/components/ScalarDistributionCard";
import { UnusedElementsCard } from "@insights-ui/components/UnusedElementsCard";
import { InsightsHostDefaults } from "@insights-ui/hostDefaults";
import {
	clearInsightsSubTab,
	closeInsightDetail,
	type InsightDetail,
	type InsightsSubTab,
	openInsightDetail,
	selectInsightDetail,
	selectInsightsSubTab,
} from "@insights-ui/state/insightDetailSlice";
import DocRootLayout from "@theme/DocRoot/Layout";
import Layout from "@theme/Layout";
import type { ComponentType, ReactNode } from "react";
import { useEffect, useState } from "react";
import { Provider } from "react-redux";
import { InsightsDetailsPane } from "@/components/InsightsDetailsPane";
import {
	INSIGHTS_ROOT_PATH,
	type InsightsCardId,
	insightsCardOfPath,
	insightsCardPath,
} from "@/insights/cards";
import type { InsightsBundle } from "@/insights/types";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { createInsightsStore, type InsightsStore } from "@/store/store";
import styles from "./insights.module.css";

type CardDefinition = {
	component: ComponentType;
	detail?: InsightDetail;
};

const CARD_DEFINITIONS = {
	"elements-breakdown": {
		component: ConceptsBreakdown,
		detail: { kind: "conceptsBreakdown" },
	},
	"composition-summary": { component: CompositionSummaryCard },
	"quality-summary": { component: QualitySummaryCard },
	"largest-container-types-by-fields": {
		component: FieldsByTypeCard,
		detail: { kind: "fieldsByType" },
	},
	"scalar-distribution": {
		component: ScalarDistributionCard,
		detail: { kind: "scalarDistribution" },
	},
	"enum-usage": {
		component: EnumUsageCard,
		detail: { kind: "enumUsage" },
	},
	"references-count": {
		component: ReferencesCountCard,
		detail: { kind: "references" },
	},
	"deepest-nested-paths": {
		component: DeepestPathsCard,
		detail: { kind: "deepestPaths" },
	},
	"cyclic-references": {
		component: CyclicReferencesCard,
		detail: { kind: "cyclicReferences" },
	},
	"documentation-coverage": {
		component: DocumentationCoverageCard,
		detail: { kind: "undocumented" },
	},
	"unused-elements": {
		component: UnusedElementsCard,
		detail: { kind: "unused" },
	},
	"missing-units": {
		component: MissingUnitsCard,
		detail: { kind: "missingUnits" },
	},
	// Every card has a definition: one added to INSIGHTS_SECTIONS without a
	// component here, or one here that no longer exists there, does not compile.
} satisfies Record<InsightsCardId, CardDefinition>;

function cardForNavigation(
	section: InsightsSubTab,
	detail: InsightDetail | null,
): InsightsCardId {
	if (detail?.kind === "unused") {
		return "unused-elements";
	}
	if (detail?.kind === "enumUsage") {
		return "enum-usage";
	}
	if (section === "composition") {
		return "largest-container-types-by-fields";
	}
	if (section === "quality") {
		return "documentation-coverage";
	}
	return "references-count";
}

function InsightsContent() {
	const dispatch = useAppDispatch();
	const history = useHistory();
	const location = useLocation();
	const insightsRootUrl = useBaseUrl(INSIGHTS_ROOT_PATH);
	const requestedSection = useAppSelector(selectInsightsSubTab);
	const detail = useAppSelector(selectInsightDetail);
	const selectedCardId = insightsCardOfPath(location.pathname, insightsRootUrl);
	const selectedCard: CardDefinition | null = selectedCardId
		? CARD_DEFINITIONS[selectedCardId]
		: null;

	useEffect(() => {
		if (selectedCard?.detail) {
			dispatch(openInsightDetail(selectedCard.detail));
			return;
		}
		dispatch(closeInsightDetail());
	}, [dispatch, selectedCard?.detail]);

	useEffect(() => {
		if (!requestedSection) {
			return;
		}
		const cardId = cardForNavigation(requestedSection, detail);
		history.push(insightsCardPath(cardId, insightsRootUrl));
		dispatch(clearInsightsSubTab());
	}, [detail, dispatch, history, insightsRootUrl, requestedSection]);

	if (!selectedCard) {
		return (
			<article className={`${styles.content} s2dm-insights`}>
				<div className={styles.status} role="alert">
					This address names no insight.
				</div>
			</article>
		);
	}

	const SelectedCard = selectedCard.component;
	return (
		<article className={`${styles.content} s2dm-insights`}>
			<SelectedCard />
			{selectedCard.detail && <InsightsDetailsPane />}
		</article>
	);
}

function InsightsLayout({
	children,
	sidebar,
}: {
	children: ReactNode;
	sidebar: PropSidebar;
}) {
	return (
		<HtmlClassNameProvider className={ThemeClassNames.wrapper.docsPages}>
			<Layout
				title="Insights"
				description="Schema composition and quality insights"
			>
				<HtmlClassNameProvider className={ThemeClassNames.page.docsDocPage}>
					<DocsSidebarProvider name="insightsSidebar" items={sidebar}>
						<DocRootLayout>{children}</DocRootLayout>
					</DocsSidebarProvider>
				</HtmlClassNameProvider>
			</Layout>
		</HtmlClassNameProvider>
	);
}

export default function InsightsPage({
	sidebar,
}: {
	sidebar: PropSidebar;
}): ReactNode {
	const insightsUrl = useBaseUrl("/insights.json");
	const [store, setStore] = useState<InsightsStore | null>(null);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		const controller = new AbortController();
		fetch(insightsUrl, { signal: controller.signal })
			.then((response) => {
				if (!response.ok) {
					throw new Error(`HTTP ${response.status}`);
				}
				return response.json() as Promise<InsightsBundle>;
			})
			.then((bundle) => setStore(createInsightsStore(bundle)))
			.catch((reason: unknown) => {
				if (!controller.signal.aborted) {
					setError(reason instanceof Error ? reason.message : "Unknown error");
				}
			});
		return () => controller.abort();
	}, [insightsUrl]);

	let content: ReactNode;
	if (error) {
		content = (
			<div className={styles.status} role="alert">
				Unable to load insights: {error}
			</div>
		);
	} else if (!store) {
		content = <div className={styles.status}>Loading insights...</div>;
	} else {
		content = (
			<Provider store={store}>
				<InsightsHostDefaults>
					<InsightsContent />
				</InsightsHostDefaults>
			</Provider>
		);
	}

	return <InsightsLayout sidebar={sidebar}>{content}</InsightsLayout>;
}
