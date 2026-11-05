import { findSchemaIssues } from "@ledger-ui/data/schemaCheck";
import type { LedgerTable } from "@ledger-ui/data/types";
import { StatusBanner } from "@shared-ui/components/status-banner";

type LedgerSchemaWarningProps = {
	tables: LedgerTable[];
};

/**
 * A warning that lists where the ledger differs from the ModL schema.
 *
 * @param tables - The tables as read from the database.
 * @returns The warning, or nothing when the ledger matches the ModL schema.
 */
export function LedgerSchemaWarning({ tables }: LedgerSchemaWarningProps) {
	const issues = findSchemaIssues(tables);
	if (issues.length === 0) {
		return null;
	}

	return (
		<StatusBanner variant={"warning"}>
			<p className={"m-0"}>This ledger does not match the ModL schema.</p>
			<ul className={"m-0 mt-1 list-disc pl-5"}>
				{issues.map((issue) => (
					<li key={issue.message}>{issue.message}</li>
				))}
			</ul>
		</StatusBanner>
	);
}
