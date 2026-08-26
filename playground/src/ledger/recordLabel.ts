import pluralize from "pluralize";
import type { LedgerRecord, LedgerValue } from "@/ledger/types";

export function shortenIdentity(value: LedgerValue): string {
	if (typeof value !== "string") {
		return String(value ?? "—");
	}
	return value.includes("/") ? value.slice(value.lastIndexOf("/") + 1) : value;
}

export function formatValue(value: LedgerValue): string {
	if (value === null) {
		return "—";
	}
	if (value instanceof Uint8Array) {
		return `${value.byteLength} bytes`;
	}
	return String(value);
}

export function recordLabel(record: LedgerRecord): string {
	const label = record.current_label ?? record.instance_label;
	return typeof label === "string" && label.length > 0 ? label : "";
}

export function recordTypeName(table: string): string {
	const singular = pluralize.singular(table);
	return singular.charAt(0).toUpperCase() + singular.slice(1);
}

export function recordStatus(record: LedgerRecord): string {
	return typeof record.status === "string" ? record.status : "";
}
