// The ledger's views in sidebar order. The links, the routes made from them and
// the view the page renders all read this. Consecutive views sharing a section
// become one sidebar category; the view without a segment is served at the root.
export const LEDGER_VIEWS = [
	{ id: "raw", label: "Raw Tables", segment: null, section: null },
	{ id: "explore", label: "Explore", segment: "explore", section: null },
	{ id: "query", label: "Query", segment: "query", section: null },
	{
		id: "structure",
		label: "Structure",
		segment: "schema/structure",
		section: "Schema",
	},
	{
		id: "diagram",
		label: "Diagram",
		segment: "schema/diagram",
		section: "Schema",
	},
] as const;

export type LedgerViewId = (typeof LEDGER_VIEWS)[number]["id"];

// The sidebar declares paths without the base URL; the plugin adds it.
export const LEDGER_ROOT_PATH = "/ledger";

export function ledgerViewPath(
	view: LedgerViewId,
	root: string = LEDGER_ROOT_PATH,
): string {
	const base = root.replace(/\/$/, "");
	const found = LEDGER_VIEWS.find((candidate) => candidate.id === view);
	return found?.segment ? `${base}/${found.segment}` : base;
}

export function ledgerViewOfPath(
	pathname: string,
	root: string = LEDGER_ROOT_PATH,
): LedgerViewId | null {
	const base = root.replace(/\/$/, "");
	const path = pathname.replace(/\/$/, "");
	if (path === base) {
		return LEDGER_VIEWS.find((view) => view.segment === null)?.id ?? null;
	}
	if (!path.startsWith(`${base}/`)) {
		return null;
	}
	const segment = path.slice(base.length + 1);
	return LEDGER_VIEWS.find((view) => view.segment === segment)?.id ?? null;
}
