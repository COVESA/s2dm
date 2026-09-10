import { InsightLinkButton } from "@insights-ui/components/InsightLinkButton";
import { recordTypeName, shortenIdentity } from "@ledger-ui/data/recordLabel";
import type { LedgerReference } from "@ledger-ui/data/references";
import type { LedgerRecord } from "@ledger-ui/data/types";
import { useLedgerDispatch } from "@ledger-ui/state/hooks";
import {
	showRecordInTable,
	viewLedgerRecord,
} from "@ledger-ui/state/ledgerSlice";

type RecordAction = LedgerReference & { column: string };

type RecordActionsProps = {
	actions: RecordAction[];
	row: { table: string } | null;
	record: LedgerRecord;
};

export function RecordActions({ actions, row, record }: RecordActionsProps) {
	const dispatch = useLedgerDispatch();

	return (
		<div className="flex flex-col items-start gap-2">
			{actions.map((action) => (
				<InsightLinkButton
					key={`${action.table}-${action.value}`}
					label={`View ${recordTypeName(action.table).toLowerCase()} ${shortenIdentity(action.value)}`}
					onClick={() =>
						dispatch(
							viewLedgerRecord({
								table: action.table,
								column: action.column,
								value: action.value,
							}),
						)
					}
				/>
			))}
			{row && (
				<InsightLinkButton
					label="Show in Raw Tables"
					onClick={() =>
						dispatch(showRecordInTable({ table: row.table, record }))
					}
				/>
			)}

			{!row && actions.length === 0 && (
				<p className="text-muted-foreground">
					This row does not point at any ledger record
				</p>
			)}
		</div>
	);
}
