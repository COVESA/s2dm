import useBaseUrl from "@docusaurus/useBaseUrl";
import { LedgerDetailsContent } from "@ledger-ui/components/LedgerDetailsContent";
import { LedgerTab } from "@ledger-ui/components/LedgerTab";
import { configureSqlJs } from "@ledger-ui/data/sqlite";
import { useLedgerDispatch, useLedgerSelector } from "@ledger-ui/state/hooks";
import {
	closeLedgerDetail,
	openLedger,
	selectLedgerDetail,
	selectLedgerError,
	selectLedgerFileName,
} from "@ledger-ui/state/ledgerSlice";
import Layout from "@theme/Layout";
import { type ReactNode, useEffect, useState } from "react";
import { Provider } from "react-redux";
import { createLedgerStore, type LedgerStore } from "@/store/ledgerStore";
import styles from "./ledger.module.css";

// The ledger this site ships. `npm run doc` copies it here from `../dist/ledger.db`,
// the same staging directory the composed schema arrives in.
const LEDGER_FILE = "/ledger.db";

function LedgerWorkspace() {
	const dispatch = useLedgerDispatch();
	const detail = useLedgerSelector(selectLedgerDetail);
	const error = useLedgerSelector(selectLedgerError);
	const fileName = useLedgerSelector(selectLedgerFileName);

	if (error) {
		return (
			<div className={styles.status} role="alert">
				Unable to read the ledger: {error}
			</div>
		);
	}

	return (
		<>
			<section className="overflow-hidden rounded-lg border border-border bg-card">
				<div className="border-b px-5 py-4">
					<span className="font-semibold text-card-foreground text-lg">
						Ledger
					</span>
					{fileName && (
						<span className="ml-2 font-mono text-muted-foreground text-sm">
							{fileName}
						</span>
					)}
				</div>
				{/* The one bounded box on the page: a grid of many rows cannot grow with
				    the document, so it scrolls inside instead. */}
				<div className={styles.workspace}>
					<LedgerTab />
				</div>
			</section>

			{detail && (
				<section className="mt-6 overflow-hidden rounded-lg border border-border bg-card">
					<LedgerDetailsContent
						onClose={() => dispatch(closeLedgerDetail())}
					/>
				</section>
			)}
		</>
	);
}

export default function LedgerPage(): ReactNode {
	const wasmUrl = useBaseUrl("/sql-wasm.wasm");
	const ledgerUrl = useBaseUrl(LEDGER_FILE);
	const [store, setStore] = useState<LedgerStore | null>(null);
	const [error, setError] = useState<string | null>(null);

	// Built in an effect, as the insights page does: every route here is
	// prerendered in Node, and nothing below the Provider may run there.
	useEffect(() => {
		const controller = new AbortController();
		configureSqlJs({ wasmUrl });
		const created = createLedgerStore();

		fetch(ledgerUrl, { signal: controller.signal })
			.then((response) => {
				if (!response.ok) {
					throw new Error(`HTTP ${response.status}`);
				}
				return response.arrayBuffer();
			})
			.then((buffer) => {
				created.dispatch(
					openLedger({
						name: LEDGER_FILE.replace(/^\//, ""),
						bytes: new Uint8Array(buffer),
					}),
				);
				setStore(created);
			})
			.catch((reason: unknown) => {
				if (!controller.signal.aborted) {
					setError(reason instanceof Error ? reason.message : "Unknown error");
				}
			});

		return () => controller.abort();
	}, [ledgerUrl, wasmUrl]);

	let content: ReactNode;
	if (error) {
		content = (
			<div className={styles.status} role="alert">
				Unable to load the ledger: {error}
			</div>
		);
	} else if (!store) {
		content = <div className={styles.status}>Loading ledger...</div>;
	} else {
		content = (
			<Provider store={store}>
				<LedgerWorkspace />
			</Provider>
		);
	}

	return (
		<Layout title="Ledger" description="Explore the project's ModL ledger">
			<main className={`${styles.page} s2dm-ledger`}>{content}</main>
		</Layout>
	);
}
