import { useId } from "react";
import type { InstancePickPopoverProps } from "@/components/explore/instancePick/InstancePickPopover";
import { InstancePickRow } from "@/components/explore/instancePick/InstancePickRow";
import { getCheckedState } from "@/utils/selectionQuery/leafCounts";

type InstancePickContentProps = InstancePickPopoverProps & {
	pickedCount: number;
};

export function InstancePickContent({
	title,
	names,
	pickedNames,
	pickedCount,
	isDisabled,
	onToggle,
}: InstancePickContentProps) {
	const idPrefix = useId();
	const allCheckedState = getCheckedState(pickedCount, names.length);
	const isLastPicked = pickedCount === 1;

	return (
		<>
			<div className={"border-b px-3 py-2 text-sm font-medium"}>{title}</div>
			<ul className={"max-h-64 overflow-y-auto py-1"}>
				<InstancePickRow
					checkboxId={`${idPrefix}-all`}
					checked={allCheckedState}
					isDisabled={isDisabled || allCheckedState === true}
					onCheckedChange={() => onToggle(names, true)}
				>
					All
				</InstancePickRow>
				{names.map((name) => {
					const isPicked = pickedNames.has(name);
					return (
						<InstancePickRow
							key={name}
							checkboxId={`${idPrefix}-${name}`}
							checked={isPicked}
							isDisabled={isDisabled || (isPicked && isLastPicked)}
							onCheckedChange={() => onToggle([name], !isPicked)}
						>
							<span className={"font-mono"}>{name}</span>
						</InstancePickRow>
					);
				})}
			</ul>
		</>
	);
}
