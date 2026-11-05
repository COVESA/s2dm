import { routePath, routeSegment } from "../utils/routes";

// The insight cards, grouped and ordered as the sidebar shows them. The links,
// the routes made from them and the card the page renders all read this.
export const INSIGHTS_SECTIONS = [
	{
		label: "Overview",
		cards: [
			{ id: "elements-breakdown", label: "Elements Breakdown" },
			{ id: "composition-summary", label: "Composition Summary" },
			{ id: "quality-summary", label: "Quality Summary" },
		],
	},
	{
		label: "Composition",
		cards: [
			{
				id: "largest-container-types-by-fields",
				label: "Largest Container Types by Fields",
			},
			{ id: "scalar-distribution", label: "Scalar Distribution" },
			{ id: "enum-usage", label: "Enum Usage" },
		],
	},
	{
		label: "Relationships",
		cards: [
			{ id: "references-count", label: "References Count" },
			{ id: "deepest-nested-paths", label: "Deepest Nested Paths" },
			{ id: "cyclic-references", label: "Cyclic References" },
		],
	},
	{
		label: "Quality",
		cards: [
			{ id: "documentation-coverage", label: "Documentation Coverage" },
			{ id: "unused-elements", label: "Unused Elements" },
			{ id: "missing-units", label: "Missing Units" },
		],
	},
] as const;

export type InsightsCardId =
	(typeof INSIGHTS_SECTIONS)[number]["cards"][number]["id"];

export type InsightsCard = { id: InsightsCardId; label: string };

export const INSIGHTS_CARDS: readonly InsightsCard[] =
	INSIGHTS_SECTIONS.flatMap((section) => [...section.cards]);

// The card served at the root rather than under a segment of its own.
export const DEFAULT_INSIGHTS_CARD: InsightsCardId = "elements-breakdown";

// The sidebar declares paths without the base URL; the plugin adds it.
export const INSIGHTS_ROOT_PATH = "/insights";

export function insightsCardPath(
	card: InsightsCardId,
	root: string = INSIGHTS_ROOT_PATH,
): string {
	let segment: string | null = card;
	if (card === DEFAULT_INSIGHTS_CARD) {
		segment = null;
	}
	return routePath(root, segment);
}

export function insightsCardOfPath(
	pathname: string,
	root: string = INSIGHTS_ROOT_PATH,
): InsightsCardId | null {
	const segment = routeSegment(pathname, root);
	if (segment === "") {
		return DEFAULT_INSIGHTS_CARD;
	}
	const found = INSIGHTS_CARDS.find((card) => card.id === segment);
	return found?.id ?? null;
}
