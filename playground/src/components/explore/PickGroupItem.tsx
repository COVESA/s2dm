import {
	TreeExpandButton,
	TreeRowFrame,
} from "@/components/explore/TreeRowParts";
import { Checkbox } from "@/components/ui/checkbox";
import { getCheckedState } from "@/utils/selectionQuery/leafCounts";
import type { PickGroupTreeRow } from "@/utils/selectionQuery/treeRows";

type PickGroupItemProps = {
	row: PickGroupTreeRow;
	label: string;
	names: string[];
	pickedNames: Set<string>;
	isDisabled: boolean;
	onToggle: (names: string[], isChecked: boolean) => void;
	onToggleExpanded: (key: string) => void;
};

export function PickGroupItem({
	row,
	label,
	names,
	pickedNames,
	isDisabled,
	onToggle,
	onToggleExpanded,
}: PickGroupItemProps) {
	const pickedCount = names.filter((name) => pickedNames.has(name)).length;
	const checkedState = getCheckedState(pickedCount, names.length);

	return (
		<TreeRowFrame depth={row.depth}>
			<TreeExpandButton
				isExpanded={row.isExpanded}
				isDisabled={row.isExpandedBySearch}
				onToggle={() => onToggleExpanded(row.key)}
			/>
			<Checkbox
				checked={checkedState}
				disabled={isDisabled}
				onCheckedChange={() => onToggle(names, checkedState !== true)}
				aria-label={`Select all ${label}`}
			/>
			<span className={"truncate text-sm font-medium text-foreground"}>
				{label}
			</span>
		</TreeRowFrame>
	);
}
