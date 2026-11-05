import { LABEL_COLUMNS } from "@ledger-ui/data/modlProfile";
import type { LedgerRecord, LedgerValue } from "@ledger-ui/data/types";
import pluralize from "pluralize";

export const ABSENT_VALUE = "—";

export function shortenIdentity(value: LedgerValue): string {
	if (typeof value !== "string") {
		return String(value ?? ABSENT_VALUE);
	}
	return value.slice(value.lastIndexOf("/") + 1);
}

export function formatValue(value: LedgerValue): string {
	if (value === null) {
		return ABSENT_VALUE;
	}
	if (value instanceof Uint8Array) {
		return `${value.byteLength} bytes`;
	}
	return String(value);
}

export function recordLabel(record: LedgerRecord): string {
	for (const column of LABEL_COLUMNS) {
		const label = record[column];
		if (typeof label === "string" && label.length > 0) {
			return label;
		}
	}
	return "";
}

function capitalise(value: string): string {
	return value.charAt(0).toUpperCase() + value.slice(1);
}

/**
 * Writes a table name as words, for example `first_second` as `First second`.
 *
 * @param table - The table name.
 * @returns The name with spaces for underscores and a capital first letter.
 */
export function tableTitle(table: string): string {
	const words = table.replaceAll("_", " ");
	return capitalise(words);
}

export function recordTypeName(table: string): string {
	const singular = pluralize.singular(table);
	return tableTitle(singular);
}
