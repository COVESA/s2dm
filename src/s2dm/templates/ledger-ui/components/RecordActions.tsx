import { InsightLinkButton } from "@insights-ui/components/InsightLinkButton";
import { recordTypeName, shortenIdentity } from "@ledger-ui/data/recordLabel";
import type { LedgerReference } from "@ledger-ui/data/references";
import { isRecordOnPage } from "@ledger-ui/data/resultRow";
import type { LedgerRecord } from "@ledger-ui/data/types";
import { useLedgerDispatch, useLedgerSelector } from "@ledger-ui/state/hooks";
import {
	selectLedgerRows,
	selectLedgerView,
	selectSelectedLedgerTable,
	showRecordInTable,
	viewLedgerRecord,
} from "@ledger-ui/state/ledgerSlice";

type RecordAction = LedgerReference & { column: string };

type RecordActionsProps = {
	actions: RecordAction[];
	storedTable: string | null;
	record: LedgerRecord;
};

/**
 * The actions for the record in the details pane: one link per ledger record it
 * points at, and a link to its row in Raw Tables unless that row is on screen.
 *
 * @param actions - The references the record holds, each with the column that
 *   finds its target.
 * @param storedTable - The table that stores the record, or `null` for a query
 *   result that no table stores.
 * @param record - The record the pane shows.
 * @returns The action links, or a note when there are none.
 */
export function RecordActions({
	actions,
	storedTable,
	record,
}: RecordActionsProps) {
	const dispatch = useLedgerDispatch();
	const view = useLedgerSelector(selectLedgerView);
	const shownTable = useLedgerSelector(selectSelectedLedgerTable);
	const pageRows = useLedgerSelector(selectLedgerRows);

	const isOnScreen =
		view === "raw" &&
		storedTable === shownTable &&
		pageRows !== null &&
		isRecordOnPage(pageRows, record);
	let tableToShow = storedTable;
	if (isOnScreen) {
		tableToShow = null;
	}

	return (
		<div className="flex flex-col items-start gap-2">
			{actions.map((action) => {
				const typeName = recordTypeName(action.table).toLowerCase();
				const shortIdentity = shortenIdentity(action.value);
				const viewAction = viewLedgerRecord(action);
				return (
					<InsightLinkButton
						key={`${action.table}-${action.value}`}
						label={`View ${typeName} ${shortIdentity}`}
						onClick={() => dispatch(viewAction)}
					/>
				);
			})}
			{tableToShow !== null && (
				<InsightLinkButton
					label="Show in Raw Tables"
					onClick={() => {
						const showAction = showRecordInTable({
							table: tableToShow,
							record,
						});
						dispatch(showAction);
					}}
				/>
			)}

			{tableToShow === null && actions.length === 0 && (
				<p className="text-muted-foreground">
					This row does not point at any ledger record
				</p>
			)}
		</div>
	);
}
