import type { Database } from "sql.js";
import { CHAIN_GROUP_FETCH_LIMIT } from "@/ledger/constants";
import { countRowsWhere, findRows, toRecords } from "@/ledger/introspect";
import type {
	LedgerRecord,
	LedgerTable,
	LedgerValue,
	QueryResult,
} from "@/ledger/types";

export type ChainLevel = {
	table: string;
	identityColumn: string;
	parentTable: string | null;
	parentColumn: string | null;
	orderColumn: string | null;
};

function levelOf(spec: ChainLevel[], table: string): ChainLevel | undefined {
	return spec.find((level) => level.table === table);
}

function childLevels(spec: ChainLevel[], table: string): ChainLevel[] {
	return spec.filter((level) => level.parentTable === table);
}

export type ChainGroup = {
	table: string;
	label: string;
	nodes: ChainNode[];
	total: number;
};

export type ChainNode = {
	table: string;
	identity: string;
	record: LedgerRecord;
	groups: ChainGroup[];
};

export type LedgerChain = {
	levels: string[];
	root: ChainNode | null;
	selected: { table: string; identity: string };
};

function identityOf(record: LedgerRecord, column: string): string {
	return String(record[column] ?? "");
}

export function deriveChainSpec(tables: LedgerTable[]): ChainLevel[] {
	const positionOf = new Map(tables.map((table, index) => [table.name, index]));

	return tables.map((table, index) => {
		// By key search, not array position: an unrelated table may sit between levels.
		let parentTable: string | null = null;
		let parentColumn: string | null = null;
		let closest = -1;
		for (const key of table.foreignKeys) {
			if (key.referencesTable === table.name) {
				continue;
			}
			const at = positionOf.get(key.referencesTable);
			if (at === undefined || at >= index || at <= closest) {
				continue;
			}
			closest = at;
			parentTable = key.referencesTable;
			parentColumn = key.column;
		}

		const referencedBy = tables
			.filter((other) => other.name !== table.name)
			.flatMap((other) => other.foreignKeys)
			.find((key) => key.referencesTable === table.name);
		const selfKey = table.foreignKeys.find(
			(key) => key.referencesTable === table.name,
		);
		const primaryKey = table.columns.find((column) => column.primaryKey);

		return {
			table: table.name,
			identityColumn:
				referencedBy?.referencesColumn ??
				selfKey?.referencesColumn ??
				primaryKey?.name ??
				table.columns[0]?.name ??
				"",
			parentTable,
			parentColumn,
			orderColumn: primaryKey?.name ?? null,
		};
	});
}

function findOne(
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

	const records = toRecords(
		findRows(database, table, column, value, {
			limit: CHAIN_GROUP_FETCH_LIMIT,
			orderBy: orderBy ?? undefined,
		}),
	);
	return { table, label, nodes: records.map(buildNode), total };
}

function buildDescendants(
	database: Database,
	spec: ChainLevel[],
	level: ChainLevel,
	record: LedgerRecord,
): ChainNode {
	const identity = identityOf(record, level.identityColumn);
	const groups: ChainGroup[] = [];

	for (const child of childLevels(spec, level.table)) {
		if (!child.parentColumn) {
			continue;
		}
		const group = buildGroup(
			database,
			child.table,
			child.table,
			child.parentColumn,
			identity,
			child.orderColumn,
			(childRecord) => buildDescendants(database, spec, child, childRecord),
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

	const selected = {
		table: selectedTable,
		identity: identityOf(selectedRecord, spec[selectedIndex].identityColumn),
	};

	let anchorLevel = spec[selectedIndex];
	let anchorRecord = selectedRecord;
	const visited = new Set<string>([anchorLevel.table]);
	while (anchorLevel.parentTable && anchorLevel.parentColumn) {
		const parent = levelOf(spec, anchorLevel.parentTable);
		// `visited` guards against a cycle in the declared keys.
		if (!parent || visited.has(parent.table)) {
			break;
		}
		const parentRecord: LedgerRecord | null = findOne(
			database,
			parent.table,
			parent.identityColumn,
			anchorRecord[anchorLevel.parentColumn] ?? null,
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
		root: buildDescendants(database, spec, anchorLevel, anchorRecord),
		selected,
	};
}
