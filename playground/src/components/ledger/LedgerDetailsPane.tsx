import { DetailsPane } from "@/components/DetailsPane";
import { DetailsPaneShell } from "@/components/DetailsPaneShell";
import { LedgerChainView } from "@/components/ledger/LedgerChainView";
import { LedgerErrorBanner } from "@/components/ledger/LedgerErrorBanner";
import { RecordActions } from "@/components/ledger/RecordActions";
import { RecordDetailsList } from "@/components/ledger/RecordDetailsList";
import { EmptyState } from "@/components/ui/empty-state";
import { Heading } from "@/components/ui/heading";
import { identityColumnFor } from "@/ledger/identity";
import { recordLabel, recordTypeName } from "@/ledger/recordLabel";
import { findLedgerReferences } from "@/ledger/references";
import type { LedgerRecord } from "@/ledger/types";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
	closeLedgerDetail,
	popLedgerDetail,
	pushLedgerDetail,
	selectCanGoBackLedgerDetail,
	selectHasLedger,
	selectIsLoadingLedgerChain,
	selectLedgerChain,
	selectLedgerChainError,
	selectLedgerDetail,
	selectLedgerTables,
} from "@/store/ledger/ledgerSlice";
import { collapseResultPane } from "@/store/ui/uiSlice";

type LedgerDetailsPaneProps = {
	position?: "none" | "left" | "center" | "right";
	collapsible?: boolean;
	className?: string;
};

export function LedgerDetailsPane({
	position = "right",
	collapsible,
	className,
}: LedgerDetailsPaneProps) {
	const dispatch = useAppDispatch();
	const detail = useAppSelector(selectLedgerDetail);
	const chain = useAppSelector(selectLedgerChain);
	const isLoading = useAppSelector(selectIsLoadingLedgerChain);
	const error = useAppSelector(selectLedgerChainError);
	const canGoBack = useAppSelector(selectCanGoBackLedgerDetail);
	const hasLedger = useAppSelector(selectHasLedger);
	const tables = useAppSelector(selectLedgerTables);

	const handleSelect = (table: string, record: LedgerRecord) => {
		dispatch(pushLedgerDetail({ kind: "row", table, record }));
	};

	const handleClose = () => {
		dispatch(closeLedgerDetail());
		dispatch(collapseResultPane());
	};

	if (!detail) {
		return (
			<DetailsPane
				className={className}
				position={position}
				collapsible={collapsible}
				hasContent={hasLedger}
			>
				<EmptyState title="Select a record to see its context" />
			</DetailsPane>
		);
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
		<DetailsPane
			className={className}
			position={position}
			collapsible={collapsible}
			hasContent={hasLedger}
		>
			<DetailsPaneShell
				title={selectedTitle}
				onClose={handleClose}
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
		</DetailsPane>
	);
}
