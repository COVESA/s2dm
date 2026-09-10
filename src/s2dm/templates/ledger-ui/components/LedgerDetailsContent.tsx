import { LedgerChainView } from "@ledger-ui/components/LedgerChainView";
import { LedgerErrorBanner } from "@ledger-ui/components/LedgerErrorBanner";
import { RecordActions } from "@ledger-ui/components/RecordActions";
import { RecordDetailsList } from "@ledger-ui/components/RecordDetailsList";
import { identityColumnFor } from "@ledger-ui/data/identity";
import { recordLabel, recordTypeName } from "@ledger-ui/data/recordLabel";
import { findLedgerReferences } from "@ledger-ui/data/references";
import type { LedgerRecord } from "@ledger-ui/data/types";
import { useLedgerDispatch, useLedgerSelector } from "@ledger-ui/state/hooks";
import {
	popLedgerDetail,
	pushLedgerDetail,
	selectCanGoBackLedgerDetail,
	selectIsLoadingLedgerChain,
	selectLedgerChain,
	selectLedgerChainError,
	selectLedgerDetail,
	selectLedgerTables,
} from "@ledger-ui/state/ledgerSlice";
import { DetailsPaneShell } from "@/components/DetailsPaneShell";
import { EmptyState } from "@/components/ui/empty-state";
import { Heading } from "@/components/ui/heading";

type LedgerDetailsContentProps = {
	// One host collapses a pane, another only clears the selection.
	onClose: () => void;
};

export function LedgerDetailsContent({ onClose }: LedgerDetailsContentProps) {
	const dispatch = useLedgerDispatch();
	const detail = useLedgerSelector(selectLedgerDetail);
	const chain = useLedgerSelector(selectLedgerChain);
	const isLoading = useLedgerSelector(selectIsLoadingLedgerChain);
	const error = useLedgerSelector(selectLedgerChainError);
	const canGoBack = useLedgerSelector(selectCanGoBackLedgerDetail);
	const tables = useLedgerSelector(selectLedgerTables);

	const handleSelect = (table: string, record: LedgerRecord) => {
		dispatch(pushLedgerDetail({ kind: "row", table, record }));
	};

	if (!detail) {
		return <EmptyState title="Select a record to see its context" />;
	}

	const selectedName =
		recordLabel(detail.record) || String(chain?.selected.identity ?? "");
	const row = detail.kind === "row" ? detail : null;
	const selectedTitle =
		`${row ? recordTypeName(row.table) : ""} ${selectedName}`.trim();
	// Anything this row points at, other than the record already on screen. Its
	// own URI is compared, not its label, so a parent in the same table is kept.
	const identityColumn = row ? identityColumnFor(tables, row.table) : null;
	const ownUri = identityColumn ? detail.record[identityColumn] : undefined;
	const tableNames = tables.map((table) => table.name);
	const references = findLedgerReferences(detail.record, tableNames).filter(
		(reference) =>
			!(reference.table === row?.table && reference.value === ownUri),
	);
	// Only references whose identity column is known can be looked up, so an
	// action is never offered that would query a column the table lacks.
	const actions = references.flatMap((reference) => {
		const column = identityColumnFor(tables, reference.table);
		return column ? [{ ...reference, column }] : [];
	});

	const cells =
		detail.kind === "projection"
			? detail.cells
			: Object.entries(detail.record).map(([column, value]) => ({
					column,
					value,
				}));

	let ledgerContext: React.ReactNode = null;
	if (error) {
		ledgerContext = <LedgerErrorBanner>{error}</LedgerErrorBanner>;
	} else if (isLoading || !chain) {
		ledgerContext = (
			<p className="text-sm text-muted-foreground">Resolving context…</p>
		);
	} else if (!chain.root) {
		// A query projection is not a record of any table, so there is no chain to
		// show and the section is left out rather than stating that.
		ledgerContext = null;
	} else {
		ledgerContext = (
			<LedgerChainView
				node={chain.root}
				selected={chain.selected}
				onSelect={handleSelect}
			/>
		);
	}

	return (
		<DetailsPaneShell
			title={selectedTitle}
			onClose={onClose}
			onBack={canGoBack ? () => dispatch(popLedgerDetail()) : undefined}
			bodyKey={`${detail.kind}:${row?.table ?? ""}:${selectedName}`}
		>
			<div className="flex flex-col gap-6 text-sm text-card-foreground">
				{ledgerContext && (
					<section className="flex flex-col gap-2">
						<Heading level="h3">Ledger context</Heading>
						{ledgerContext}
					</section>
				)}

				<section className="flex flex-col gap-2">
					<Heading level="h3">Record details</Heading>
					<RecordDetailsList cells={cells} />
				</section>

				<section className="flex flex-col gap-2">
					<Heading level="h3">Actions</Heading>
					<RecordActions actions={actions} row={row} record={detail.record} />
				</section>
			</div>
		</DetailsPaneShell>
	);
}
