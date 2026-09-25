import { identityColumnOf } from "@/ledger/identity";
import type { LedgerRecord, LedgerTable } from "@/ledger/types";

export type ChainParent = {
	table: string;
	column: string;
	identityColumn: string;
};

export type ChainLevel = {
	table: string;
	identityColumn: string | null;
	parent: ChainParent | null;
	orderColumn: string | null;
};

export function levelOf(
	spec: ChainLevel[],
	table: string,
): ChainLevel | undefined {
	return spec.find((level) => level.table === table);
}

export function childLevels(spec: ChainLevel[], table: string): ChainLevel[] {
	return spec.filter((level) => level.parent?.table === table);
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

export function identityOf(
	record: LedgerRecord,
	column: string | null,
): string {
	return column === null ? "" : String(record[column] ?? "");
}

export function chainNodeKey(node: {
	table: string;
	identity: string;
}): string {
	return `${node.table}:${node.identity}`;
}

// Every node from the root down to the selected one. A node holds the selection
// below it when the set contains it and it is not the selection itself.
export function selectedAncestry(
	root: ChainNode | null,
	selected: { table: string; identity: string },
): Set<string> {
	const ancestry = new Set<string>();

	const walk = (node: ChainNode, path: string[]): boolean => {
		const trail = [...path, chainNodeKey(node)];
		if (node.table === selected.table && node.identity === selected.identity) {
			for (const key of trail) {
				ancestry.add(key);
			}
			return true;
		}
		for (const group of node.groups) {
			for (const child of group.nodes) {
				if (walk(child, trail)) {
					return true;
				}
			}
		}
		return false;
	};

	if (root) {
		walk(root, []);
	}
	return ancestry;
}

export function deriveChainSpec(tables: LedgerTable[]): ChainLevel[] {
	const positionOf = new Map(tables.map((table, index) => [table.name, index]));
	const columnsOf = new Map(
		tables.map((table) => [
			table.name,
			new Set(table.columns.map((column) => column.name)),
		]),
	);

	return tables.map((table, index) => {
		const primaryKey = table.columns.find((column) => column.primaryKey);
		return {
			table: table.name,
			identityColumn: identityColumnOf(table),
			parent: findNearestParent(table, index, positionOf, columnsOf),
			orderColumn: primaryKey?.name ?? null,
		};
	});
}

// The closest preceding table this one points at, by key search rather than by
// array position: an unrelated table may sit between two levels.
function findNearestParent(
	table: LedgerTable,
	index: number,
	positionOf: Map<string, number>,
	columnsOf: Map<string, Set<string>>,
): ChainParent | null {
	let parent: ChainParent | null = null;
	let closestPosition = -1;

	for (const key of table.foreignKeys) {
		// A level has one parent table, so a self reference would make it its own
		// ancestor. Drops parent_uri and previous_revision_uri from the tree.
		if (key.referencesTable === table.name) {
			continue;
		}
		const parentPosition = positionOf.get(key.referencesTable);
		if (
			parentPosition === undefined ||
			parentPosition >= index ||
			parentPosition <= closestPosition
		) {
			continue;
		}
		// A rowid target is real to SQLite but absent from SELECT *, so it cannot
		// identify a parent record here.
		if (!columnsOf.get(key.referencesTable)?.has(key.referencesColumn)) {
			continue;
		}
		closestPosition = parentPosition;
		parent = {
			table: key.referencesTable,
			column: key.column,
			identityColumn: key.referencesColumn,
		};
	}

	return parent;
}
