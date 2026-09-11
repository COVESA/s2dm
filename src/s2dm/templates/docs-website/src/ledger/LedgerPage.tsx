import type { PropSidebar } from "@docusaurus/plugin-content-docs";
import { DocsSidebarProvider } from "@docusaurus/plugin-content-docs/client";
import { useHistory, useLocation } from "@docusaurus/router";
import {
	HtmlClassNameProvider,
	ThemeClassNames,
} from "@docusaurus/theme-common";
import useBaseUrl from "@docusaurus/useBaseUrl";
import { ExploreView } from "@ledger-ui/components/ExploreView";
import { LedgerDetailsContent } from "@ledger-ui/components/LedgerDetailsContent";
import { LedgerOverview } from "@ledger-ui/components/LedgerOverview";
import { QueryView } from "@ledger-ui/components/QueryView";
import { RawTablesView } from "@ledger-ui/components/RawTablesView";
import { configureSqlJs } from "@ledger-ui/data/sqlite";
import { useLedgerDispatch, useLedgerSelector } from "@ledger-ui/state/hooks";
import {
	closeLedgerDetail,
	type LedgerView,
	openLedger,
	selectHasLedger,
	selectLedgerDetail,
	selectLedgerError,
	selectLedgerRows,
	selectLedgerView,
	setLedgerView,
} from "@ledger-ui/state/ledgerSlice";
import DocRootLayout from "@theme/DocRoot/Layout";
import Layout from "@theme/Layout";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { Provider } from "react-redux";
import {
	type LedgerSession,
	openLedgerOnce,
	releaseLedgerSession,
} from "@/store/ledgerStore";
import styles from "./ledger.module.css";

// `npm run doc` copies it here from `../dist/ledger.db`, where the schema lands too.
const LEDGER_FILE = "/ledger.db";

const DEFAULT_VIEW: LedgerView = "schema";
const VIEW_SEGMENTS: Record<string, LedgerView> = {
	raw: "raw",
	explore: "explore",
	query: "query",
};

function getView(pathname: string): LedgerView {
	const segment = pathname.split("/").filter(Boolean).at(-1);
	return (segment && VIEW_SEGMENTS[segment]) || DEFAULT_VIEW;
}

function getViewPath(view: LedgerView, ledgerRootUrl: string): string {
	if (view === DEFAULT_VIEW) {
		return ledgerRootUrl;
	}
	return `${ledgerRootUrl.replace(/\/$/, "")}/${view}`;
}

function LedgerViewPanel() {
	const view = useLedgerSelector(selectLedgerView);

	if (view === "raw") {
		return <RawTablesView />;
	}
	if (view === "explore") {
		return <ExploreView />;
	}
	if (view === "query") {
		return <QueryView />;
	}
	return (
		<div className={styles.schema}>
			<LedgerOverview />
		</div>
	);
}

function LedgerContent() {
	const dispatch = useLedgerDispatch();
	const history = useHistory();
	const location = useLocation();
	const ledgerRootUrl = useBaseUrl("/ledger");
	const detail = useLedgerSelector(selectLedgerDetail);
	const error = useLedgerSelector(selectLedgerError);
	const hasLedger = useLedgerSelector(selectHasLedger);
	const view = useLedgerSelector(selectLedgerView);
	const rows = useLedgerSelector(selectLedgerRows);
	const urlView = getView(location.pathname);
	const reconciledView = useRef<LedgerView | null>(null);
	const workspaceRef = useRef<HTMLElement>(null);

	// The sidebar navigates and the store switches view on its own, so whichever
	// side moved since the last reconcile wins.
	useEffect(() => {
		if (reconciledView.current !== urlView) {
			reconciledView.current = urlView;
			if (view !== urlView) {
				dispatch(setLedgerView(urlView));
			}
			return;
		}
		if (view !== urlView) {
			reconciledView.current = view;
			history.replace(getViewPath(view, ledgerRootUrl));
		}
	}, [dispatch, history, ledgerRootUrl, urlView, view]);

	// The grid scrolls its selected row into view, but only as far as its own
	// scroll box, so the page never follows. Keyed on the rows because the
	// table and the page can both be unchanged.
	useEffect(() => {
		workspaceRef.current?.scrollIntoView({
			behavior: "smooth",
			block: "nearest",
		});
	}, [view, rows]);

	let body: ReactNode;
	if (error) {
		body = (
			<div className={styles.status} role="alert">
				Unable to read the ledger: {error}
			</div>
		);
	} else if (!hasLedger) {
		body = <div className={styles.status}>Reading the ledger...</div>;
	} else {
		body = (
			<>
				<section className={styles.workspaceCard} ref={workspaceRef}>
					{/* The one bounded box on the page: a grid of many rows cannot grow
					    with the document, so it scrolls inside instead. */}
					<div
						className={
							view === "schema" ? styles.schemaWorkspace : styles.workspace
						}
					>
						<LedgerViewPanel />
					</div>
				</section>

				{/* Only the views that list records: the schema view has nothing to
				    select, so neither the details nor an invitation to select
				    belongs under it. A selection made elsewhere survives. */}
				{view !== "schema" &&
					(detail ? (
						<section className="mt-6 overflow-hidden rounded-lg border border-border bg-card">
							<LedgerDetailsContent
								onClose={() => dispatch(closeLedgerDetail())}
							/>
						</section>
					) : (
						<p className="mt-6 text-center text-muted-foreground text-sm">
							Select a record to see its context, details and actions.
						</p>
					))}
			</>
		);
	}

	return <article className={`${styles.content} s2dm-ledger`}>{body}</article>;
}

function LedgerLayout({
	children,
	sidebar,
}: {
	children: ReactNode;
	sidebar: PropSidebar;
}) {
	return (
		<HtmlClassNameProvider className={ThemeClassNames.wrapper.docsPages}>
			<Layout title="Ledger" description="Explore the project's ModL ledger">
				<HtmlClassNameProvider className={ThemeClassNames.page.docsDocPage}>
					<DocsSidebarProvider name="ledgerSidebar" items={sidebar}>
						<DocRootLayout>{children}</DocRootLayout>
					</DocsSidebarProvider>
				</HtmlClassNameProvider>
			</Layout>
		</HtmlClassNameProvider>
	);
}

export default function LedgerPage({
	sidebar,
}: {
	sidebar: PropSidebar;
}): ReactNode {
	const history = useHistory();
	const wasmUrl = useBaseUrl("/sql-wasm.wasm");
	const ledgerUrl = useBaseUrl(LEDGER_FILE);
	const ledgerRootUrl = useBaseUrl("/ledger");
	const [session, setSession] = useState<LedgerSession | null>(null);

	// In an effect because every route here is prerendered in Node, and nothing
	// below the Provider may run there.
	useEffect(() => {
		configureSqlJs({ wasmUrl });
		setSession(
			openLedgerOnce({
				url: ledgerUrl,
				name: LEDGER_FILE.replace(/^\//, ""),
			}),
		);
	}, [ledgerUrl, wasmUrl]);

	// On leaving the ledger, not on unmount: each view is its own route.
	useEffect(() => {
		const root = ledgerRootUrl.replace(/\/$/, "");
		return history.listen((next) => {
			if (next.pathname !== root && !next.pathname.startsWith(`${root}/`)) {
				releaseLedgerSession();
			}
		});
	}, [history, ledgerRootUrl]);

	let content: ReactNode;
	if (!session) {
		content = <div className={styles.status}>Loading ledger...</div>;
	} else {
		content = (
			<Provider store={session.store}>
				<LedgerContent />
			</Provider>
		);
	}

	return <LedgerLayout sidebar={sidebar}>{content}</LedgerLayout>;
}
