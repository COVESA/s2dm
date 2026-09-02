import { LedgerBadge } from "@/components/ledger/LedgerBadge";
import { LedgerErdButton } from "@/components/ledger/LedgerErdButton";
import { tableIcon } from "@/components/ledger/tableIcon";
import { EmptyState } from "@/components/ui/empty-state";
import { capitalise } from "@/ledger/recordLabel";
import { useAppSelector } from "@/store/hooks";
import {
	selectIsLoadingLedger,
	selectLedgerTables,
} from "@/store/ledger/ledgerSlice";

export function LedgerOverview() {
	const tables = useAppSelector(selectLedgerTables);
	const isLoading = useAppSelector(selectIsLoadingLedger);

	if (isLoading) {
		return <EmptyState isLoading title="Reading ledger..." />;
	}

	if (tables.length === 0) {
		return <EmptyState title="Nothing to display" />;
	}

	const totalRecords = tables.reduce(
		(total, table) => total + table.rowCount,
		0,
	);

	return (
		<div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4">
			<div className="flex items-baseline justify-between gap-2">
				<span className="text-sm text-muted-foreground">Records</span>
				<span className="text-sm tabular-nums">{totalRecords}</span>
			</div>

			<dl className="flex flex-col divide-y divide-border overflow-hidden rounded-md border">
				{tables.map((table) => {
					const Icon = tableIcon(table.name);
					return (
						<div key={table.name} className="bg-background/50 px-3 py-2">
							<div className="flex items-center justify-between gap-2">
								<dt className="flex min-w-0 items-center gap-2 text-sm">
									<Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
									<span className="truncate">{capitalise(table.name)}</span>
								</dt>
								<dd className="flex shrink-0 items-center gap-2">
									{table.activeCount !== null && (
										<LedgerBadge
											tone="active"
											title={`${table.activeCount} active`}
										>
											{table.activeCount}
										</LedgerBadge>
									)}
									<span className="text-sm text-muted-foreground tabular-nums">
										{table.rowCount}
									</span>
								</dd>
							</div>
							<ul className="mt-2 flex flex-col">
								{table.columns.map((column) => (
									<li
										key={column.name}
										className="flex items-baseline justify-between gap-2 font-mono text-xs text-muted-foreground"
									>
										<span className="truncate">
											{column.name}
											{column.primaryKey && " ·pk"}
										</span>
										<span className="shrink-0 opacity-70">
											{column.declaredType}
										</span>
									</li>
								))}
							</ul>
						</div>
					);
				})}
			</dl>

			<LedgerErdButton />
		</div>
	);
}
