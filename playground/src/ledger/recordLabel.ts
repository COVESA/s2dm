import pluralize from "pluralize";
import { LABEL_COLUMNS } from "@/ledger/modlProfile";
import type { LedgerRecord, LedgerValue } from "@/ledger/types";

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

export function capitalise(value: string): string {
	return value.charAt(0).toUpperCase() + value.slice(1);
}

export function recordTypeName(table: string): string {
	return capitalise(pluralize.singular(table));
}

export function recordStatus(record: LedgerRecord): string {
	return typeof record.status === "string" ? record.status : "";
}
