import type { CheckedState } from "@radix-ui/react-checkbox";
import type { ReactNode } from "react";
import { LabelCheckbox } from "@/components/ui/checkbox";

type InstancePickRowProps = {
	checkboxId: string;
	checked: CheckedState;
	isDisabled: boolean;
	onCheckedChange: () => void;
	children: ReactNode;
};

export function InstancePickRow({
	checkboxId,
	checked,
	isDisabled,
	onCheckedChange,
	children,
}: InstancePickRowProps) {
	return (
		<li className={"px-3 py-1"}>
			<LabelCheckbox
				id={checkboxId}
				checked={checked}
				disabled={isDisabled}
				onCheckedChange={onCheckedChange}
			>
				{children}
			</LabelCheckbox>
		</li>
	);
}
