import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import type { ChainGroup, ChainNode } from "@/ledger/chain";
import {
	CHAIN_AUTO_EXPAND_DEPTH,
	CHAIN_GROUP_RENDER_LIMIT,
} from "@/ledger/constants";
import {
	recordLabel,
	recordTypeName,
	shortenIdentity,
} from "@/ledger/recordLabel";
import type { LedgerRecord } from "@/ledger/types";
import { cn } from "@/utils/cn";

type SelectedRef = { table: string; identity: string };

function containsSelected(node: ChainNode, selected: SelectedRef): boolean {
	if (node.table === selected.table && node.identity === selected.identity) {
		return true;
	}
	return node.groups.some((group) =>
		group.nodes.some((child) => containsSelected(child, selected)),
	);
}

function GroupView({
	group,
	selected,
	depth,
	autoOpenRemaining,
	onSelect,
}: {
	group: ChainGroup;
	selected: SelectedRef;
	depth: number;
	autoOpenRemaining: number;
	onSelect: (table: string, record: LedgerRecord) => void;
}) {
	const [isExpanded, setIsExpanded] = useState(false);

	// Order is never changed; the group opens instead of hoisting the selection.
	const selectedIndex = group.nodes.findIndex((node) =>
		containsSelected(node, selected),
	);
	const showAll = isExpanded || selectedIndex >= CHAIN_GROUP_RENDER_LIMIT;
	const visible = showAll
		? group.nodes
		: group.nodes.slice(0, CHAIN_GROUP_RENDER_LIMIT);

	// Only the fetched rows can be revealed; the rest are reported separately.
	const hidden = group.nodes.length - visible.length;
	const notFetched = group.total - group.nodes.length;

	return (
		<div className="flex flex-col gap-1">
			{visible.map((node, index) => (
				<NodeView
					// Identity can be empty when its column is null, which would
					// collapse siblings onto one key.
					key={`${node.table}-${node.identity || index}`}
					node={node}
					selected={selected}
					depth={depth}
					autoOpenRemaining={autoOpenRemaining}
					onSelect={onSelect}
				/>
			))}

			{hidden > 0 && !showAll && (
				<button
					type="button"
					onClick={() => setIsExpanded(true)}
					style={{ marginLeft: `${depth * 12}px` }}
					className="cursor-pointer rounded-md px-2 py-1 text-left font-mono text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
				>
					See {hidden} more {group.label}
				</button>
			)}

			{showAll && notFetched > 0 && (
				<p
					style={{ marginLeft: `${depth * 12}px` }}
					className="px-2 py-1 font-mono text-xs text-muted-foreground"
				>
					{notFetched} more not loaded
				</p>
			)}
		</div>
	);
}

function NodeView({
	node,
	selected,
	depth,
	autoOpenRemaining,
	onSelect,
}: {
	node: ChainNode;
	selected: SelectedRef;
	depth: number;
	autoOpenRemaining: number;
	onSelect: (table: string, record: LedgerRecord) => void;
}) {
	// null until the user decides for themselves, so the automatic state can
	// change with the selection without discarding an explicit choice.
	const [override, setOverride] = useState<boolean | null>(null);

	const isSelected =
		node.table === selected.table && node.identity === selected.identity;
	const label = recordLabel(node.record);
	const groups = node.groups;
	const hasChildren = groups.length > 0;

	// Ancestors stay open so the selection is always reachable.
	const holdsSelectionBelow = groups.some((group) =>
		group.nodes.some((child) => containsSelected(child, selected)),
	);
	const budget = isSelected ? CHAIN_AUTO_EXPAND_DEPTH : autoOpenRemaining;
	const openByDefault = holdsSelectionBelow || budget > 0;
	const isOpen =
		hasChildren && (holdsSelectionBelow || (override ?? openByDefault));

	const handleClick = () => {
		if (!isSelected) {
			onSelect(node.table, node.record);
			return;
		}
		if (!hasChildren) {
			return;
		}
		setOverride(!(override ?? openByDefault));
	};

	let chevron: React.ReactNode = <span className="h-3 w-3 shrink-0" />;
	if (hasChildren) {
		chevron = isOpen ? (
			<ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" />
		) : (
			<ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />
		);
	}

	return (
		<div className="flex flex-col gap-1">
			<button
				type="button"
				onClick={handleClick}
				style={{ marginLeft: `${depth * 12}px` }}
				className={cn(
					"flex w-full cursor-pointer items-center gap-2 rounded-md border px-2 py-1.5 text-left transition-colors",
					isSelected
						? "border-primary bg-accent"
						: "border-transparent hover:bg-muted",
				)}
				aria-current={isSelected ? "true" : undefined}
				aria-expanded={hasChildren ? isOpen : undefined}
			>
				{chevron}
				<span className="shrink-0 font-mono text-xs text-muted-foreground">
					{recordTypeName(node.table)}
				</span>
				<span className="min-w-0 flex-1 truncate font-mono text-xs">
					{label || shortenIdentity(node.identity)}
				</span>
			</button>

			{isOpen &&
				groups.map((group) => (
					<GroupView
						key={`${node.identity}-${group.table}-${group.label}`}
						group={group}
						selected={selected}
						depth={depth + 1}
						autoOpenRemaining={budget - 1}
						onSelect={onSelect}
					/>
				))}
		</div>
	);
}

type LedgerChainViewProps = {
	node: ChainNode;
	selected: SelectedRef;
	onSelect: (table: string, record: LedgerRecord) => void;
};

export function LedgerChainView({
	node,
	selected,
	onSelect,
}: LedgerChainViewProps) {
	return (
		<NodeView
			// Remounts on a new selection so automatic expansion applies afresh.
			key={`${selected.table}:${selected.identity}`}
			node={node}
			selected={selected}
			depth={0}
			autoOpenRemaining={0}
			onSelect={onSelect}
		/>
	);
}
