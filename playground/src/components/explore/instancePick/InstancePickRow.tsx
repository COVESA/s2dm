import type { CheckedState } from "@radix-ui/react-checkbox";
import type { ReactNode } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { FormLabel } from "@/components/ui/form-label";

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
		<li className={"flex items-center gap-2 px-3 py-1"}>
			<Checkbox
				id={checkboxId}
				checked={checked}
				disabled={isDisabled}
				onCheckedChange={onCheckedChange}
			/>
			<FormLabel
				htmlFor={checkboxId}
				className={"flex-1 cursor-pointer text-sm"}
			>
				{children}
			</FormLabel>
		</li>
	);
}
