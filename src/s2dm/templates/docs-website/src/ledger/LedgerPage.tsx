import type { PropSidebar } from "@docusaurus/plugin-content-docs";
import { useHistory, useLocation } from "@docusaurus/router";
import useBaseUrl from "@docusaurus/useBaseUrl";
import { ExploreView } from "@ledger-ui/components/ExploreView";
import { LedgerDetailsContent } from "@ledger-ui/components/LedgerDetailsContent";
import { LedgerErdDiagram } from "@ledger-ui/components/LedgerErdDiagram";
import { LedgerOverview } from "@ledger-ui/components/LedgerOverview";
import { QueryView } from "@ledger-ui/components/QueryView";
import { RawTablesView } from "@ledger-ui/components/RawTablesView";
import { configureLedgerWorker } from "@ledger-ui/data/ledgerClient";
import { useLedgerDispatch, useLedgerSelector } from "@ledger-ui/state/hooks";
import {
	closeLedgerDetail,
	selectLedgerDetail,
	selectLedgerError,
	selectLedgerRows,
	selectLedgerStatus,
	selectLedgerView,
	setLedgerView,
} from "@ledger-ui/state/ledgerSlice";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { Provider } from "react-redux";
import { ContentPageLayout } from "@/components/ContentPageLayout";
import {
	type LedgerSession,
	openLedgerOnce,
	releaseLedgerSession,
} from "@/store/ledgerStore";
import styles from "./ledger.module.css";
import {
	LEDGER_ROOT_PATH,
	type LedgerViewId,
	ledgerViewOfPath,
	ledgerViewPath,
} from "./views";

// `npm run doc` copies it here from `../dist/ledger.db`, where the schema lands too.
const LEDGER_FILE = "/ledger.db";

// A view added to LEDGER_VIEWS without a panel here does not compile.
const VIEW_PANELS: Record<LedgerViewId, () => ReactNode> = {
	raw: () => <RawTablesView />,
	explore: () => <ExploreView />,
	query: () => <QueryView />,
	structure: () => <LedgerOverview />,
	diagram: () => <LedgerErdDiagram fit className="p-6" />,
};

// Neither schema view lists records, so they grow with the page and have
// nothing for the details panel to describe.
const SCHEMA_VIEWS: readonly LedgerViewId[] = ["structure", "diagram"];

function LedgerViewPanel() {
	const view = useLedgerSelector(selectLedgerView);
	return VIEW_PANELS[view]();
}

function LedgerContent() {
	const dispatch = useLedgerDispatch();
	const history = useHistory();
	const location = useLocation();
	const ledgerRootUrl = useBaseUrl(LEDGER_ROOT_PATH);
	const detail = useLedgerSelector(selectLedgerDetail);
	const error = useLedgerSelector(selectLedgerError);
	const status = useLedgerSelector(selectLedgerStatus);
	const view = useLedgerSelector(selectLedgerView);
	const isSchemaView = SCHEMA_VIEWS.includes(view);
	const rows = useLedgerSelector(selectLedgerRows);
	const urlView = ledgerViewOfPath(location.pathname, ledgerRootUrl);
	const reconciledView = useRef<LedgerViewId | null>(null);
	const workspaceRef = useRef<HTMLElement>(null);

	// Sidebar and store both switch view, so whichever moved last wins.
	useEffect(() => {
		if (urlView === null) {
			return;
		}
		if (reconciledView.current !== urlView) {
			reconciledView.current = urlView;
			if (view !== urlView) {
				dispatch(setLedgerView(urlView));
			}
			return;
		}
		if (view !== urlView) {
			reconciledView.current = view;
			history.replace(ledgerViewPath(view, ledgerRootUrl));
		}
	}, [dispatch, history, ledgerRootUrl, urlView, view]);

	// The grid scrolls a selected row only as far as its own box, so the page
	// never follows. Keyed on the rows: the table and the page can be unchanged.
	// biome-ignore lint/correctness/useExhaustiveDependencies: the deps are what the scroll follows, not values the effect reads.
	useEffect(() => {
		workspaceRef.current?.scrollIntoView({
			behavior: "smooth",
			block: "nearest",
		});
	}, [view, rows]);

	let body: ReactNode;
	if (urlView === null) {
		body = (
			<div className={styles.status} role="alert">
				This address names no ledger view.
			</div>
		);
	} else if (error) {
		body = (
			<div className={styles.status} role="alert">
				Unable to read the ledger: {error}
			</div>
		);
	} else if (status === "empty") {
		body = (
			<div className={styles.status}>
				This ledger holds no tables, so there is nothing to show.
			</div>
		);
	} else if (status !== "ready") {
		// Idle too: the fetch starts before the store hears of it.
		body = <div className={styles.status}>Reading the ledger...</div>;
	} else {
		body = (
			<>
				<section className={styles.workspaceCard} ref={workspaceRef}>
					{/* The one bounded box on the page: a grid of many rows cannot grow
					    with the document, so it scrolls inside instead. */}
					<div
						className={
							isSchemaView ? styles.schemaWorkspace : styles.workspace
						}
					>
						<LedgerViewPanel />
					</div>
				</section>

				{/* Only the views that list records: a schema view has nothing to
				    select, so neither the details nor an invitation to select
				    belongs under it. A selection made elsewhere survives. */}
				{!isSchemaView &&
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

export default function LedgerPage({
	sidebar,
}: {
	sidebar: PropSidebar;
}): ReactNode {
	const history = useHistory();
	const wasmUrl = useBaseUrl("/sql-wasm.wasm");
	const ledgerUrl = useBaseUrl(LEDGER_FILE);
	const ledgerRootUrl = useBaseUrl(LEDGER_ROOT_PATH);
	const [session, setSession] = useState<LedgerSession | null>(null);
	// The sidebar is empty when `npm run doc` staged no ledger.
	const hasLedger = sidebar.length > 0;

	// In an effect: every route here is prerendered in Node.
	useEffect(() => {
		if (!hasLedger) {
			return;
		}
		configureLedgerWorker({ wasmUrl });
		setSession(
			openLedgerOnce({
				url: ledgerUrl,
				name: LEDGER_FILE.replace(/^\//, ""),
			}),
		);
	}, [hasLedger, ledgerUrl, wasmUrl]);

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
	if (!hasLedger) {
		content = <div className={styles.status}>No ledger is available.</div>;
	} else if (!session) {
		content = <div className={styles.status}>Loading ledger...</div>;
	} else {
		content = (
			<Provider store={session.store}>
				<LedgerContent />
			</Provider>
		);
	}

	return (
		<ContentPageLayout
			title={"Ledger"}
			description={"Explore the project's ModL ledger"}
			sidebarName={"ledgerSidebar"}
			sidebar={sidebar}
		>
			{content}
		</ContentPageLayout>
	);
}
