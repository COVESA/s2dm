// The ledger's views in sidebar order. The links, the routes made from them and
// the view the page renders all read this.
export const LEDGER_VIEWS = [
	{ id: "schema", label: "Schema", segment: null },
	{ id: "raw", label: "Raw Tables", segment: "raw" },
	{ id: "explore", label: "Explore", segment: "explore" },
	{ id: "query", label: "Query", segment: "query" },
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
