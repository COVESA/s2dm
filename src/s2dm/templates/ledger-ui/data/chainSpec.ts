import { identityColumnsOf } from "@ledger-ui/data/identity";
import { primaryKeyColumnsOf } from "@ledger-ui/data/schema";
import type { LedgerRecord, LedgerTable } from "@ledger-ui/data/types";

export type ChainParent = {
	table: string;
	column: string;
	identityColumn: string;
};

export type ChainLevel = {
	table: string;
	identityColumns: string[];
	parent: ChainParent | null;
	orderColumns: string[];
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

/**
 * Writes the identity of a record as one string that compares by value, so a
 * record keyed by several columns still has one identity. The values form a
 * JSON array, so a value that contains a separator stays apart from the next.
 *
 * @param record - The record to identify.
 * @param columns - The identity columns of the record's table.
 * @returns The values of the columns as a JSON array. Empty when every value
 *   is empty or there are no columns.
 */
export function identityOf(record: LedgerRecord, columns: string[]): string {
	const values = columns.map((column) => String(record[column] ?? ""));
	const isEmpty = values.every((value) => value === "");
	if (isEmpty) {
		return "";
	}
	return JSON.stringify(values);
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
		const identityColumns = identityColumnsOf(table);
		const parent = findNearestParent(table, index, positionOf, columnsOf);
		const orderColumns = primaryKeyColumnsOf(table.columns);
		return { table: table.name, identityColumns, parent, orderColumns };
	});
}

/**
 * Finds the closest preceding table that a table points at. It searches by
 * key rather than by array position, because an unrelated table may sit
 * between two levels.
 *
 * @param table - The table to find the parent of.
 * @param index - The position of the table in the ordered tables.
 * @param positionOf - The position of each table, by name.
 * @param columnsOf - The column names of each table, by table name.
 * @returns The parent table, the key column that points at it and the column
 *   it references, or `null` when there is none.
 */
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
		if (parentPosition === undefined || parentPosition >= index) {
			continue;
		}
		// Of several keys to the same table, the one named after the column it
		// references is the record's own link: contract_references.contract_uri,
		// not target_contract_uri, which SQLite lists first.
		const isCloser = parentPosition > closestPosition;
		const isNamedLink =
			parentPosition === closestPosition && key.column === key.referencesColumn;
		if (!isCloser && !isNamedLink) {
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
