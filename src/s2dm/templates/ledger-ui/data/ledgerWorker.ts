/// <reference lib="webworker" />
import { findOne, resolveChain } from "@ledger-ui/data/chainResolve";
import { searchLedger } from "@ledger-ui/data/ledgerSearch";
import { runReadQuery } from "@ledger-ui/data/query";
import { storedRecordTable } from "@ledger-ui/data/resultRecord";
import {
	countSearchMatches,
	listDistinctValues,
	type RowFilters,
	rowPageIndex,
	searchTable,
} from "@ledger-ui/data/rows";
import { readSchema } from "@ledger-ui/data/schema";
import type { SearchOptions } from "@ledger-ui/data/search";
import {
	closeLedgerDatabase,
	getLedgerDatabase,
	setLedgerDatabase,
} from "@ledger-ui/data/session";
import { configureSqlJs, openLedgerDatabase } from "@ledger-ui/data/sqlite";
import type {
	LedgerRecord,
	LedgerTable,
	LedgerValue,
} from "@ledger-ui/data/types";

// Read once when the ledger opens: every operation that needs them runs here, so
// they never have to cross the thread boundary with the request.
let tables: LedgerTable[] = [];

// The database lives on this thread. SQLite steps a statement to completion with
// no way to interrupt it, so a slow query stops this worker and not the page.
const operations = {
	async open(payload: { bytes: Uint8Array; wasmUrl: string }) {
		configureSqlJs({ wasmUrl: payload.wasmUrl });
		const database = await openLedgerDatabase(payload.bytes);
		setLedgerDatabase(database);
		tables = readSchema(database);
		return tables;
	},

	close() {
		closeLedgerDatabase();
		tables = [];
	},

	listDistinctValues(payload: { table: string; column: string }) {
		return listDistinctValues(
			getLedgerDatabase(),
			payload.table,
			payload.column,
		);
	},

	searchTable(payload: {
		table: string;
		needle: string;
		limit: number;
		offset: number;
		filters: RowFilters;
		search: SearchOptions;
	}) {
		return searchTable(getLedgerDatabase(), payload.table, payload.needle, {
			limit: payload.limit,
			offset: payload.offset,
			filters: payload.filters,
			search: payload.search,
		});
	},

	countSearchMatches(payload: {
		table: string;
		needle: string;
		filters: RowFilters;
		search: SearchOptions;
	}) {
		return countSearchMatches(
			getLedgerDatabase(),
			payload.table,
			payload.needle,
			{
				filters: payload.filters,
				search: payload.search,
			},
		);
	},

	searchLedger(payload: {
		needle: string;
		limit: number;
		search: SearchOptions;
	}) {
		return searchLedger(getLedgerDatabase(), tables, payload.needle, {
			limit: payload.limit,
			search: payload.search,
		});
	},

	resolveChain(payload: { table: string; record: LedgerRecord }) {
		return resolveChain(
			getLedgerDatabase(),
			tables,
			payload.table,
			payload.record,
		);
	},

	rowPageIndex(payload: {
		table: string;
		record: LedgerRecord;
		pageSize: number;
	}) {
		return rowPageIndex(
			getLedgerDatabase(),
			payload.table,
			payload.record,
			payload.pageSize,
		);
	},

	findOne(payload: { table: string; column: string; value: LedgerValue }) {
		return findOne(
			getLedgerDatabase(),
			payload.table,
			payload.column,
			payload.value,
		);
	},

	runQuery(payload: { sql: string }) {
		return runReadQuery(getLedgerDatabase(), payload.sql);
	},

	storedRecordTable(payload: { columns: string[]; record: LedgerRecord }) {
		return storedRecordTable(
			getLedgerDatabase(),
			payload.columns,
			payload.record,
			tables,
		);
	},
};

export type LedgerOperations = typeof operations;
export type LedgerOperation = keyof LedgerOperations;

export type LedgerRequest = {
	id: number;
	operation: LedgerOperation;
	payload: unknown;
};

export type LedgerResponse =
	| { id: number; ok: true; value: unknown }
	| { id: number; ok: false; message: string; name: string };

self.onmessage = async (event: MessageEvent<LedgerRequest>) => {
	const { id, operation, payload } = event.data;
	try {
		// The dispatch table is keyed by operation name, which no signature can
		// prove matches the payload the caller sent; the client's types do.
		const run = operations[operation] as (input: unknown) => unknown;
		const value = await run(payload);
		self.postMessage({ id, ok: true, value } satisfies LedgerResponse);
	} catch (error) {
		const failure = error instanceof Error ? error : new Error(String(error));
		self.postMessage({
			id,
			ok: false,
			message: failure.message,
			name: failure.name,
		} satisfies LedgerResponse);
	}
};
