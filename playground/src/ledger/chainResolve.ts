import type { Database } from "sql.js";
import {
	type ChainGroup,
	type ChainLevel,
	type ChainNode,
	childLevels,
	deriveChainSpec,
	identityOf,
	type LedgerChain,
	levelOf,
} from "@/ledger/chainSpec";
import { countRowsWhere, findRows, toRecords } from "@/ledger/introspect";
import type {
	LedgerRecord,
	LedgerTable,
	LedgerValue,
	QueryResult,
} from "@/ledger/types";

// How many children of one parent are fetched. The view shows far fewer, but
// expanding must not need a second query.
const CHAIN_GROUP_FETCH_LIMIT = 100;

// Descendants multiply per level, so the walk stops expanding after this many
// nodes. Groups past it still list their rows, without their own children.
const CHAIN_NODE_BUDGET = 300;

export function findOne(
	database: Database,
	table: string,
	column: string,
	value: LedgerValue,
): LedgerRecord | null {
	const result: QueryResult = findRows(database, table, column, value, {
		limit: 1,
	});
	return toRecords(result)[0] ?? null;
}

// One level of children under a parent value: the true total by count, and a
// capped page of records, each expanded by the caller's buildNode.
function buildGroup(
	database: Database,
	table: string,
	label: string,
	column: string,
	value: string,
	orderBy: string | null,
	buildNode: (record: LedgerRecord) => ChainNode,
): ChainGroup | null {
	if (value === "") {
		return null;
	}

	const total = countRowsWhere(database, table, column, value);
	if (total === 0) {
		return null;
	}

	const page = findRows(database, table, column, value, {
		limit: CHAIN_GROUP_FETCH_LIMIT,
		orderBy: orderBy ?? undefined,
	});
	const records = toRecords(page);
	return { table, label, nodes: records.map(buildNode), total };
}

function buildDescendants(
	database: Database,
	spec: ChainLevel[],
	level: ChainLevel,
	record: LedgerRecord,
	// Mutated: one budget is shared by the whole walk.
	budget: { remaining: number },
): ChainNode {
	const identity = identityOf(record, level.identityColumn);
	const groups: ChainGroup[] = [];

	const children = childLevels(spec, level.table);
	for (const child of children) {
		if (!child.parent) {
			continue;
		}
		const group = buildGroup(
			database,
			child.table,
			child.table,
			child.parent.column,
			identityOf(record, child.parent.identityColumn),
			child.orderColumn,
			(childRecord) => {
				if (budget.remaining <= 0) {
					return {
						table: child.table,
						identity: identityOf(childRecord, child.identityColumn),
						record: childRecord,
						groups: [],
					};
				}
				budget.remaining -= 1;
				return buildDescendants(database, spec, child, childRecord, budget);
			},
		);
		if (group) {
			groups.push(group);
		}
	}

	return { table: level.table, identity, record, groups };
}

export function resolveChain(
	database: Database,
	tables: LedgerTable[],
	selectedTable: string,
	selectedRecord: LedgerRecord,
): LedgerChain {
	const spec = deriveChainSpec(tables);
	const levels = spec.map((level) => level.table);
	const selectedIndex = spec.findIndex(
		(level) => level.table === selectedTable,
	);

	if (selectedIndex === -1) {
		return {
			levels,
			root: null,
			selected: { table: selectedTable, identity: "" },
		};
	}

	const selectedLevel = spec[selectedIndex];
	if (!selectedLevel) {
		return {
			levels,
			root: null,
			selected: { table: selectedTable, identity: "" },
		};
	}

	const selected = {
		table: selectedTable,
		identity: identityOf(selectedRecord, selectedLevel.identityColumn),
	};

	let anchorLevel: ChainLevel = selectedLevel;
	let anchorRecord = selectedRecord;
	const visited = new Set<string>([anchorLevel.table]);
	while (anchorLevel.parent) {
		const parentLink = anchorLevel.parent;
		const parent = levelOf(spec, parentLink.table);
		// `visited` guards against a cycle in the declared keys.
		if (!parent || visited.has(parent.table)) {
			break;
		}
		const parentRecord: LedgerRecord | null = findOne(
			database,
			parent.table,
			parentLink.identityColumn,
			anchorRecord[parentLink.column] ?? null,
		);
		if (!parentRecord) {
			break;
		}
		anchorRecord = parentRecord;
		anchorLevel = parent;
		visited.add(parent.table);
	}

	return {
		levels,
		root: buildDescendants(database, spec, anchorLevel, anchorRecord, {
			remaining: CHAIN_NODE_BUDGET,
		}),
		selected,
	};
}
