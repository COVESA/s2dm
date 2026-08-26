import { InsightLinkButton } from "@insights-ui/components/InsightLinkButton";
import { ArrowLeft, X } from "lucide-react";
import { DetailsPane } from "@/components/DetailsPane";
import { LedgerChainView } from "@/components/ledger/LedgerChainView";
import { StatusBadge } from "@/components/ledger/StatusBadge";
import { Heading } from "@/components/ui/heading";
import { StatusBanner } from "@/components/ui/status-banner";
import { identityColumnFor } from "@/ledger/identity";
import {
	formatValue,
	recordLabel,
	recordStatus,
	recordTypeName,
	shortenIdentity,
} from "@/ledger/recordLabel";
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
	showRecordInTable,
	viewLedgerRecord,
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
		dispatch(pushLedgerDetail({ table, record }));
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
				<div className="flex flex-1 items-center justify-center p-5 text-center text-muted-foreground">
					<p>Select a record to see its context</p>
				</div>
			</DetailsPane>
		);
	}

	const selectedName =
		recordLabel(detail.record) || String(chain?.selected.identity ?? "");
	const selectedTitle =
		`${recordTypeName(detail.table)} ${selectedName}`.trim();
	const selectedStatus = recordStatus(detail.record);
	// Anything this row points at, other than the record already on screen. Its
	// own URI is compared, not its label, so a parent in the same table is kept.
	const ownUri =
		detail.table === ""
			? undefined
			: detail.record[identityColumnFor(tables, detail.table)];
	const references = findLedgerReferences(
		detail.record,
		tables.map((table) => table.name),
	).filter(
		(reference) =>
			!(reference.table === detail.table && reference.value === ownUri),
	);

	let ledgerContext: React.ReactNode = null;
	if (error) {
		ledgerContext = (
			<StatusBanner variant="destructive" className="whitespace-pre-wrap">
				{error}
			</StatusBanner>
		);
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
			<div className="flex h-full flex-col">
				<div className="flex items-center justify-between gap-2 border-b px-5 py-4">
					<div className="flex min-w-0 items-center gap-2">
						{canGoBack && (
							<button
								type="button"
								onClick={() => dispatch(popLedgerDetail())}
								className="shrink-0 cursor-pointer rounded-md p-1 text-muted-foreground hover:bg-muted"
								aria-label="Back"
							>
								<ArrowLeft className="h-4 w-4" />
							</button>
						)}
						<span
							className="truncate text-lg font-semibold text-card-foreground"
							title={selectedTitle}
						>
							{selectedTitle}
						</span>
					</div>
					<div className="flex shrink-0 items-center gap-2">
						{selectedStatus && <StatusBadge status={selectedStatus} />}
						<button
							type="button"
							onClick={handleClose}
							className="shrink-0 cursor-pointer rounded-md p-1 text-muted-foreground hover:bg-muted"
							aria-label="Close details"
						>
							<X className="h-4 w-4" />
						</button>
					</div>
				</div>

				<div className="flex flex-1 animate-in flex-col gap-6 overflow-y-auto px-5 pt-5 pb-14 text-sm text-card-foreground fade-in slide-in-from-right-4 duration-200">
					{ledgerContext && (
						<section className="flex flex-col gap-2">
							<Heading level="h3">Ledger context</Heading>
							{ledgerContext}
						</section>
					)}

					<section className="flex flex-col gap-2">
						<Heading level="h3">Record details</Heading>
						<dl className="flex flex-col gap-px">
							{Object.entries(detail.record).map(([key, value]) => (
								<div
									key={key}
									className="flex items-baseline justify-between gap-3 py-0.5"
								>
									<dt className="shrink-0 font-mono text-muted-foreground text-xs">
										{key}
									</dt>
									<dd
										className="min-w-0 truncate font-mono text-xs"
										title={formatValue(value)}
									>
										{formatValue(value)}
									</dd>
								</div>
							))}
						</dl>
					</section>

					<section className="flex flex-col gap-2">
						<Heading level="h3">Actions</Heading>
						<div className="flex flex-col items-start gap-1">
							{references.map((reference) => (
								<InsightLinkButton
									key={`${reference.table}-${reference.value}`}
									label={`View ${recordTypeName(reference.table).toLowerCase()} ${shortenIdentity(reference.value)}`}
									onClick={() =>
										dispatch(
											viewLedgerRecord({
												table: reference.table,
												column: identityColumnFor(tables, reference.table),
												value: reference.value,
											}),
										)
									}
								/>
							))}
							{detail.table !== "" && (
								<InsightLinkButton
									label="Show in Raw Tables"
									onClick={() =>
										dispatch(
											showRecordInTable({
												table: detail.table,
												record: detail.record,
											}),
										)
									}
								/>
							)}

							{detail.table === "" && references.length === 0 && (
								<p className="text-muted-foreground">
									This row does not point at any ledger record
								</p>
							)}
						</div>
					</section>
				</div>
			</div>
		</DetailsPane>
	);
}
