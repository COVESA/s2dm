import { InstancePickPopover } from "@/components/explore/instancePick/InstancePickPopover";
import {
	SelectionTreeItem,
	type SelectionTreeItemProps,
} from "@/components/explore/SelectionTreeItem";
import type { InstancePickTarget } from "@/utils/selectionQuery/instanceTag";
import { resolveFieldPickedNames } from "@/utils/selectionQuery/pick";
import {
	type InstancePicks,
	readPickState,
} from "@/utils/selectionQuery/readInstancePick";
import { getSegmentKey } from "@/utils/selectionQuery/schemaTree";

type InstanceTagTreeItemProps = Omit<SelectionTreeItemProps, "labelAccessory"> & {
	pickTarget: InstancePickTarget;
	instancePicks: InstancePicks;
	onInstancePickToggle: (
		pickTarget: InstancePickTarget,
		toggledNames: string[],
		isChecked: boolean,
	) => void;
};

export function InstanceTagTreeItem({
	pickTarget,
	instancePicks,
	onInstancePickToggle,
	...itemProps
}: InstanceTagTreeItemProps) {
	const { row, countLeaves, isDisabled } = itemProps;
	const { selectedCount } = countLeaves(row.node);
	const isSelected = selectedCount > 0;
	const { dimensionName, pickableNames } = pickTarget;
	const { listedNames, isOtherFormPicked } = readPickState(
		instancePicks,
		pickTarget,
	);
	const pickedNames = resolveFieldPickedNames(listedNames, pickableNames);
	const isPickDisabled =
		isDisabled || row.isBeyondCycleDepth || !isSelected || isOtherFormPicked;

	let fieldName = "";
	if (row.node.segment) {
		fieldName = getSegmentKey(row.node.segment);
	}

	let title = `Instances of ${fieldName}`;
	if (dimensionName !== null) {
		title = `Values of ${fieldName}`;
	}

	const handlePickToggle = (toggledNames: string[], isChecked: boolean) =>
		onInstancePickToggle(pickTarget, toggledNames, isChecked);

	const pickPopover = (
		<InstancePickPopover
			title={title}
			names={pickableNames}
			pickedNames={pickedNames}
			isDisabled={isPickDisabled}
			onToggle={handlePickToggle}
		/>
	);

	return <SelectionTreeItem {...itemProps} labelAccessory={pickPopover} />;
}
