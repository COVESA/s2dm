import { ArrowLeft, X } from "lucide-react";
import { DetailsPane } from "@/components/DetailsPane";
import { LedgerChainView } from "@/components/ledger/LedgerChainView";
import { StatusBadge } from "@/components/ledger/StatusBadge";
import { StatusBanner } from "@/components/ui/status-banner";
import {
	recordLabel,
	recordStatus,
	recordTypeName,
} from "@/ledger/recordLabel";
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
} from "@/store/ledger/ledgerSlice";
import { collapseResultPane } from "@/store/ui/uiSlice";

type LedgerDetailsPaneProps = {
	position?: "none" | "left" | "center" | "right";
	collapsible?: boolean;
	className?: string;
};

function Section({
	title,
	children,
}: {
	title: string;
	children: React.ReactNode;
}) {
	return (
		<section className="flex flex-col gap-2">
			<h3 className="font-medium text-[11px] text-muted-foreground uppercase tracking-wide">
				{title}
			</h3>
			{children}
		</section>
	);
}

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

	let ledgerContext: React.ReactNode;
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
		ledgerContext = (
			<p className="text-sm text-muted-foreground">
				This record has no related context.
			</p>
		);
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

				<div className="flex flex-1 animate-in flex-col gap-6 overflow-y-auto px-5 pt-5 pb-14 fade-in slide-in-from-right-4 duration-200">
					<Section title="Ledger context">{ledgerContext}</Section>

					<Section title="Record details">
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
										title={value === null ? "" : String(value)}
									>
										{value === null ? "—" : String(value)}
									</dd>
								</div>
							))}
						</dl>
					</Section>

					<Section title="Actions">
						<p className="text-muted-foreground text-sm">
							No actions available yet
						</p>
					</Section>
				</div>
			</div>
		</DetailsPane>
	);
}
