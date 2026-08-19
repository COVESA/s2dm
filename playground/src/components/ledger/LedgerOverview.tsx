import { tableIcon } from "@/components/ledger/tableIcon";
import { EmptyState } from "@/components/ui/empty-state";
import { useAppSelector } from "@/store/hooks";
import {
	selectIsLoadingLedger,
	selectLedgerTables,
	selectLedgerView,
} from "@/store/ledger/ledgerSlice";

export function LedgerOverview() {
	const tables = useAppSelector(selectLedgerTables);
	const isLoading = useAppSelector(selectIsLoadingLedger);
	const view = useAppSelector(selectLedgerView);
	const showSchema = view === "query";

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
	const relationships = tables.flatMap((table) =>
		table.foreignKeys.map((key) => ({ table: table.name, ...key })),
	);

	return (
		<div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4">
			<div className="flex items-baseline justify-between gap-2">
				<span className="text-sm text-muted-foreground">Records</span>
				<span className="font-mono text-sm tabular-nums">{totalRecords}</span>
			</div>

			<dl className="flex flex-col gap-px overflow-hidden rounded-md border">
				{tables.map((table) => {
					const Icon = tableIcon(table.name);
					return (
						<div key={table.name} className="bg-background px-3 py-2">
							<div className="flex items-center justify-between gap-2">
								<dt className="flex min-w-0 items-center gap-2 text-sm">
									<Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
									<span className="truncate capitalize">{table.name}</span>
								</dt>
								<dd className="flex shrink-0 items-baseline gap-1.5 font-mono text-sm tabular-nums">
									{table.activeCount !== null && (
										<span
											className="text-emerald-700 dark:text-emerald-300"
											title={`${table.activeCount} active`}
										>
											&lt;{table.activeCount}&gt;
										</span>
									)}
									<span className="text-muted-foreground">
										{table.rowCount}
									</span>
								</dd>
							</div>
							{showSchema && (
								<ul className="mt-1 flex flex-col">
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
							)}
						</div>
					);
				})}
			</dl>

			{showSchema && relationships.length > 0 && (
				<div className="flex flex-col gap-1">
					<p className="text-xs font-medium text-muted-foreground">
						Relationships
					</p>
					{relationships.map((key) => (
						<p
							key={`${key.table}-${key.column}-${key.referencesTable}`}
							className="font-mono text-xs text-muted-foreground"
						>
							{key.table}.{key.column} → {key.referencesTable}.
							{key.referencesColumn}
						</p>
					))}
				</div>
			)}
		</div>
	);
}
