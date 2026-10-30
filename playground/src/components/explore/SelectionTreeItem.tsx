import { Repeat } from "lucide-react";
import type { ReactNode } from "react";
import {
	TreeDocsLink,
	TreeExpandButton,
	TreeExpandSpacer,
	TreeRowFrame,
} from "@/components/explore/TreeRowParts";
import { Checkbox } from "@/components/ui/checkbox";
import {
	getCheckedState,
	type LeafCounts,
} from "@/utils/selectionQuery/leafCounts";
import {
	getSegmentKey,
	type SchemaTreeNode,
} from "@/utils/selectionQuery/schemaTree";
import type { FieldTreeRow } from "@/utils/selectionQuery/treeRows";

export type SelectionTreeItemProps = {
	row: FieldTreeRow;
	countLeaves: (node: SchemaTreeNode) => LeafCounts;
	isDisabled: boolean;
	/** A control shown after the field name. */
	labelAccessory?: ReactNode;
	onToggle: (node: SchemaTreeNode, isChecked: boolean) => void;
	onToggleExpanded: (key: string) => void;
	onShowDocs: (node: SchemaTreeNode) => void;
};

export function SelectionTreeItem({
	row,
	countLeaves,
	isDisabled,
	labelAccessory,
	onToggle,
	onToggleExpanded,
	onShowDocs,
}: SelectionTreeItemProps) {
	const {
		node,
		depth,
		isBeyondCycleDepth,
		isExpandable,
		isExpanded,
		isExpandedBySearch,
		highlightTerm,
	} = row;
	const { selectedCount, totalCount } = countLeaves(node);
	const checkedState = getCheckedState(selectedCount, totalCount);

	let label = "";
	if (node.segment) {
		label = getSegmentKey(node.segment);
	}

	let expandControl: ReactNode = <TreeExpandSpacer />;
	if (isExpandable) {
		expandControl = (
			<TreeExpandButton
				isExpanded={isExpanded}
				isDisabled={isExpandedBySearch}
				onToggle={() => onToggleExpanded(node.key)}
			/>
		);
	}

	let recursionHint =
		"Cyclic field: its type already appears higher up this branch. Selecting it includes one level; expand it to go deeper.";
	if (isBeyondCycleDepth) {
		recursionHint =
			"Cyclic field beyond the cycle depth: raise the cycle depth to expand or select it.";
	}

	return (
		<TreeRowFrame depth={depth} isMuted={isBeyondCycleDepth}>
			{expandControl}
			<Checkbox
				checked={checkedState}
				disabled={isDisabled || isBeyondCycleDepth || totalCount === 0}
				onCheckedChange={() => onToggle(node, checkedState !== true)}
				aria-label={`Select ${label}`}
			/>
			<TreeDocsLink
				label={label}
				highlightTerm={highlightTerm}
				onClick={() => onShowDocs(node)}
			/>
			{labelAccessory}
			<span
				className={"min-w-0 truncate font-mono text-xs text-muted-foreground"}
				title={node.typeLabel}
			>
				{node.typeLabel}
			</span>
			{node.isRecursive && (
				<span
					className={"shrink-0 text-muted-foreground"}
					title={recursionHint}
				>
					<Repeat className={"size-3.5"} />
				</span>
			)}
		</TreeRowFrame>
	);
}
